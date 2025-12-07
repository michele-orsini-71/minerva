"""
Repository watcher implementation with file system monitoring and indexing pipeline.
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Set

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent


logger = logging.getLogger(__name__)


class RepositoryEventHandler(FileSystemEventHandler):
    """Handle file system events for repository changes."""

    def __init__(self, watcher: 'RepositoryWatcher'):
        self.watcher = watcher
        super().__init__()

    def on_any_event(self, event: FileSystemEvent) -> None:
        """Handle any file system event."""
        # Skip directory events
        if event.is_directory:
            return

        # Get the file path
        file_path = Path(event.src_path)

        # Check if file should be tracked
        if not self.watcher.should_track_file(file_path):
            return

        # Log the change
        relative_path = file_path.relative_to(self.watcher.repository_path)
        if self.watcher.dry_run:
            logger.info(f"File change detected: {relative_path}")
        else:
            logger.debug(f"Change detected: {relative_path}")

        # Add to pending files
        self.watcher.enqueue_change(file_path)


class RepositoryWatcher:
    """Watch a repository and trigger Minerva indexing on changes."""

    def __init__(self, config: Dict[str, Any], run_initial_index: bool = True, dry_run: bool = False):
        """
        Initialize the repository watcher.

        Args:
            config: Configuration dictionary with repository_path, collection_name, etc.
            run_initial_index: Whether to run initial indexing on startup
            dry_run: If True, log commands without executing them
        """
        self.config = config
        self.repository_path = Path(config['repository_path']).resolve()
        self.collection_name = config['collection_name']
        self.extracted_json_path = Path(config['extracted_json_path']).resolve()
        self.index_config_path = Path(config['index_config_path']).resolve()
        self.dry_run = dry_run

        # Watch configuration
        self.include_extensions = config.get('include_extensions', [
            '.md', '.mdx', '.markdown', '.rst', '.txt'
        ])
        self.ignore_patterns = config.get('ignore_patterns', [
            '.git', 'node_modules', '.venv', '__pycache__',
            '.pytest_cache', 'dist', 'build', '.tox'
        ])

        # Debouncing
        self.debounce_seconds = config.get('debounce_seconds', 60.0)
        self.pending_files: Set[Path] = set()
        self.last_change_time: float = 0
        self.debounce_timer = None

        # State
        self.observer = None
        self.running = False
        self.pipeline_in_progress = False
        self.awaiting_change_after_failure = False
        self.run_initial_index = run_initial_index

        # Validate paths (skip in dry-run mode)
        if not self.repository_path.exists():
            raise ValueError(f"Repository path does not exist: {self.repository_path}")
        if not dry_run and not self.index_config_path.exists():
            raise ValueError(f"Index config not found: {self.index_config_path}")

    def should_track_file(self, file_path: Path) -> bool:
        """Check if a file should trigger indexing."""
        # Check if in ignore patterns
        try:
            relative = file_path.relative_to(self.repository_path)
            for pattern in self.ignore_patterns:
                if pattern in relative.parts:
                    return False
        except ValueError:
            # File is outside repository
            return False

        # Check extension
        if self.include_extensions:
            return file_path.suffix.lower() in self.include_extensions

        return True

    def enqueue_change(self, file_path: Path) -> None:
        """Add a file change to the pending queue and schedule a run."""
        self.pending_files.add(file_path)

        # Only update last_change_time if pipeline is not in progress
        # This prevents resetting the debounce timer during pipeline execution
        if not self.pipeline_in_progress:
            self.last_change_time = time.time()

        # Clear failure state when new changes arrive
        if self.awaiting_change_after_failure:
            logger.info("New changes detected, clearing failure state")
            self.awaiting_change_after_failure = False

        # Schedule debounced run
        self.schedule_run()

    def schedule_run(self) -> None:
        """Schedule a pipeline run after debounce period."""
        # This will be checked by the main loop
        pass

    def check_and_run_pipeline(self) -> None:
        """Check if it's time to run the pipeline and execute if ready."""
        # Don't run if pipeline is already in progress
        if self.pipeline_in_progress:
            return

        # Don't run if waiting for changes after a failure
        if self.awaiting_change_after_failure:
            return

        # Don't run if no pending files
        if not self.pending_files:
            return

        # Check if debounce period has elapsed
        time_since_last_change = time.time() - self.last_change_time
        if time_since_last_change < self.debounce_seconds:
            return

        # Run the pipeline
        self.run_pipeline()

    def run_pipeline(self) -> None:
        """Execute the extraction and indexing pipeline."""
        if not self.pending_files and not self.run_initial_index:
            return

        self.pipeline_in_progress = True

        # Snapshot the pending files before processing
        files_to_process = set(self.pending_files)
        self.pending_files.clear()

        try:
            if files_to_process:
                file_count = len(files_to_process)
                logger.info(f"Running pipeline for {file_count} changed file(s)")
                # Always show which files triggered the pipeline
                for file_path in sorted(files_to_process):
                    relative = file_path.relative_to(self.repository_path)
                    logger.info(f"  • {relative}")
            else:
                logger.info("Running initial indexing")

            # Step 1: Extract repository
            logger.info("Extracting repository contents...")
            self.run_extraction()

            # Step 2: Index collection
            logger.info("Indexing collection...")
            self.run_indexing()

            logger.info("✓ Pipeline complete")
            self.awaiting_change_after_failure = False

            # Clear initial index flag after first successful run
            self.run_initial_index = False

        except Exception as e:
            logger.error(f"❌ Pipeline failed: {str(e)}")
            # Log full error details for debugging
            import traceback
            logger.debug(f"Full error traceback:\n{traceback.format_exc()}")
            self.awaiting_change_after_failure = True
            # Don't clear pending_files on failure - they were already cleared above
            # Any new changes that arrived during the failed run are still in pending_files

        finally:
            self.pipeline_in_progress = False
            # Reset debounce timer after pipeline completes
            # This ensures that any changes detected during the pipeline run
            # will respect the full debounce period before triggering again
            if self.pending_files:
                self.last_change_time = time.time()

    def run_extraction(self) -> None:
        """Run repository extraction."""
        cmd = [
            'repository-doc-extractor',
            str(self.repository_path),
            '-o',
            str(self.extracted_json_path)
        ]

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would execute: {' '.join(cmd)}")
            logger.info(f"[DRY-RUN]   Output: {self.extracted_json_path}")
            return

        logger.debug(f"Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            error_output = result.stderr or result.stdout or "No error output"
            raise RuntimeError(f"Extraction failed:\n{error_output}")

        logger.debug("Extraction complete")

    def run_indexing(self) -> None:
        """Run Minerva indexing."""
        cmd = [
            'minerva',
            'index',
            '--config',
            str(self.index_config_path)
        ]

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would execute: {' '.join(cmd)}")
            logger.info(f"[DRY-RUN]   Config: {self.index_config_path}")
            logger.info(f"[DRY-RUN]   Collection: {self.collection_name}")
            return

        logger.debug(f"Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            error_output = result.stderr or result.stdout or "No error output"
            raise RuntimeError(f"Indexing failed:\n{error_output}")

        logger.debug("Indexing complete")

    def start(self) -> None:
        """Start watching the repository."""
        if self.running:
            logger.warning("Watcher is already running")
            return

        self.running = True

        # Run initial indexing if requested
        if self.run_initial_index:
            logger.info("Running initial indexing on startup...")
            try:
                self.run_pipeline()
            except Exception as e:
                logger.error(f"Initial indexing failed: {e}")
                logger.info("Will retry when files change")

        # Start file system observer
        self.observer = Observer()
        event_handler = RepositoryEventHandler(self)
        self.observer.schedule(
            event_handler,
            str(self.repository_path),
            recursive=True
        )
        self.observer.start()

        logger.info(f"Watching: {self.repository_path}")
        logger.info(f"Debounce: {self.debounce_seconds}s")
        logger.info(f"Extensions: {', '.join(self.include_extensions) if self.include_extensions else 'all'}")

        # Run check loop in background
        import threading
        self.check_thread = threading.Thread(target=self._check_loop, daemon=True)
        self.check_thread.start()

    def _check_loop(self) -> None:
        """Background loop to check for pending pipeline runs."""
        while self.running:
            self.check_and_run_pipeline()
            time.sleep(0.5)

    def stop(self) -> None:
        """Stop watching the repository."""
        if not self.running:
            return

        logger.info("Stopping watcher...")
        self.running = False

        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)

        logger.info("Watcher stopped")

import os
import sys
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

# Import ChromaDB client initialization from existing pipeline
from minervium.indexing.storage import initialize_chromadb_client
from minervium.common.logger import get_logger

# Initialize console logger (simple mode for CLI usage)
console_logger = get_logger(__name__, simple=True)


class ValidationError(Exception):
    """Base exception for validation errors."""
    pass


def validate_chromadb_path(chromadb_path: str) -> Tuple[bool, Optional[str]]:
    # Check if path is provided
    if not chromadb_path or not chromadb_path.strip():
        return (False,
            "ChromaDB path is empty or not configured\n"
            "\n"
            "  Please verify your config.json file contains:\n"
            "  {\n"
            "    \"chromadb_path\": \"/absolute/path/to/chromadb_data\",\n"
            "    ...\n"
            "  }\n"
            "\n"
            "  Remediation steps:\n"
            "  1. Open your config.json file\n"
            "  2. Ensure 'chromadb_path' is set to an absolute path\n"
            "  3. Verify the path points to your ChromaDB storage directory"
        )

    # Check if path exists
    path = Path(chromadb_path)
    if not path.exists():
        return (False,
            f"ChromaDB path does not exist: {chromadb_path}\n"
            "\n"
            "  The configured ChromaDB directory was not found on the filesystem.\n"
            "\n"
            "  Remediation steps:\n"
            "  1. Verify the path in config.json is correct:\n"
            f"     Current path: {chromadb_path}\n"
            "\n"
            "  2. If the path is incorrect, update config.json with the correct path\n"
            "\n"
            "  3. If you haven't created a ChromaDB database yet, run the pipeline:\n"
            "     cd markdown-notes-cag-data-creator\n"
            "     python full_pipeline.py ../test-data/your-notes.json\n"
            "\n"
            "  4. Ensure the ChromaDB path in config.json matches where the pipeline\n"
            "     created the database (default: ../chromadb_data)"
        )

    # Check if path is a directory
    if not path.is_dir():
        return (False,
            f"ChromaDB path is not a directory: {chromadb_path}\n"
            "\n"
            "  The configured path exists but is a file, not a directory.\n"
            "\n"
            "  Remediation steps:\n"
            "  1. Check that the path in config.json points to a directory\n"
            "  2. ChromaDB storage requires a directory to store collections\n"
            "  3. Update config.json with the correct directory path"
        )

    # Check if directory is readable
    if not os.access(chromadb_path, os.R_OK):
        return (False,
            f"ChromaDB path is not readable: {chromadb_path}\n"
            "\n"
            "  Permission denied when trying to access the directory.\n"
            "\n"
            "  Remediation steps:\n"
            "  1. Check directory permissions:\n"
            f"     ls -la {chromadb_path}\n"
            "\n"
            "  2. Ensure your user has read access:\n"
            f"     chmod +r {chromadb_path}\n"
            "\n"
            "  3. If the directory is owned by another user, check ownership"
        )

    return (True, None)


def validate_collection_availability(chromadb_path: str) -> Tuple[bool, Optional[str]]:
    try:
        # Initialize ChromaDB client
        client = initialize_chromadb_client(chromadb_path)

        # List all collections
        collections = client.list_collections()

        if not collections or len(collections) == 0:
            return (False,
                "No collections found in ChromaDB\n"
                "\n"
                "  The ChromaDB database exists but contains no collections.\n"
                "  You need to create at least one collection before using the MCP server.\n"
                "\n"
                "  Remediation steps:\n"
                "  1. Run the RAG pipeline to create a collection from your notes:\n"
                "     cd markdown-notes-cag-data-creator\n"
                "     python full_pipeline.py --verbose ../test-data/your-notes.json\n"
                "\n"
                "  2. The pipeline will create embeddings and store them in ChromaDB\n"
                "\n"
                "  3. Verify collections were created:\n"
                "     python -c \"import chromadb; client = chromadb.PersistentClient(path='" + chromadb_path + "'); print([c.name for c in client.list_collections()])\"\n"
                "\n"
                "  4. Restart the MCP server once collections are available"
            )

        return (True, None)

    except Exception as e:
        return (False,
            f"Failed to connect to ChromaDB or list collections\n"
            "\n"
            f"  Error: {str(e)}\n"
            "\n"
            "  Remediation steps:\n"
            "  1. Verify the ChromaDB path in config.json is correct:\n"
            f"     Current path: {chromadb_path}\n"
            "\n"
            "  2. Check if the ChromaDB database is corrupted:\n"
            "     - Try listing collections manually (see command above)\n"
            "     - Check ChromaDB logs for errors\n"
            "\n"
            "  3. If the database is corrupted, you may need to recreate it:\n"
            "     - Back up the directory first\n"
            "     - Rerun the RAG pipeline to create a fresh database"
        )


def validate_server_prerequisites(config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    chromadb_path = config.get('chromadb_path', '')

    # Validation 1: ChromaDB path exists and is accessible
    success, error = validate_chromadb_path(chromadb_path)
    if not success:
        return (False, f"ChromaDB Path Validation Failed:\n\n{error}")

    # Validation 2: At least one collection exists
    success, error = validate_collection_availability(chromadb_path)
    if not success:
        return (False, f"Collection Availability Check Failed:\n\n{error}")

    # All validations passed
    return (True, None)


if __name__ == "__main__":
    import json
    from config import load_config, get_config_file_path

    try:
        # Load configuration
        config_path = sys.argv[1] if len(sys.argv) > 1 else get_config_file_path()
        config = load_config(config_path)

        console_logger.info("Running server validation checks...\n")

        # Run validation
        success, error = validate_server_prerequisites(config)

        if success:
            console_logger.success("✓ All validation checks passed!")
            console_logger.info("\nServer is ready to start.")
            sys.exit(0)
        else:
            console_logger.error(f"Validation failed:\n\n{error}")
            sys.exit(1)

    except Exception as e:
        console_logger.error(f"Validation error: {e}")
        sys.exit(1)

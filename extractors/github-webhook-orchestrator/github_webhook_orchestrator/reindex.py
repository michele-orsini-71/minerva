import os
import subprocess
import logging
from pathlib import Path
from .config import RepositoryConfig

logger = logging.getLogger(__name__)


def detect_markdown_changes(commits: list) -> bool:
    if not commits:
        return False

    for commit in commits:
        if not isinstance(commit, dict):
            continue

        for file_list_key in ['added', 'modified', 'removed']:
            files = commit.get(file_list_key, [])
            if not isinstance(files, list):
                continue

            for file_path in files:
                if not isinstance(file_path, str):
                    continue

                if file_path.endswith('.md') or file_path.endswith('.mdx'):
                    return True

    return False


def execute_reindex(repo_config: RepositoryConfig) -> bool:
    try:
        logger.info(f"[1/4] Running git pull in {repo_config.local_path} (branch: {repo_config.branch})")
        result = _run_git_pull(repo_config.local_path, repo_config.branch)
        if not result:
            logger.error("[1/4] Git pull failed")
            return False
        logger.info("[1/4] Git pull succeeded")

        extracted_json = _get_extracted_json_path(repo_config.index_config)

        logger.info(f"[2/4] Running extractor: {repo_config.local_path} -> {extracted_json}")
        result = _run_extractor(repo_config.local_path, extracted_json)
        if not result:
            logger.error("[2/4] Extraction failed")
            return False
        logger.info("[2/4] Extraction succeeded")

        logger.info(f"[3/4] Validating extracted JSON: {extracted_json}")
        result = _run_validation(extracted_json)
        if not result:
            logger.error("[3/4] Validation failed")
            return False
        logger.info("[3/4] Validation succeeded")

        logger.info(f"[4/4] Running indexing with config: {repo_config.index_config}")
        result = _run_indexing(repo_config.index_config)
        if not result:
            logger.error("[4/4] Indexing failed")
            return False
        logger.info("[4/4] Indexing succeeded")

        return True

    except Exception as e:
        logger.error(f"Unexpected error during reindex: {e}")
        return False


def _run_git_pull(local_path: str, branch: str) -> bool:
    try:
        result = subprocess.run(
            ['git', 'pull', 'origin', branch],
            cwd=local_path,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            logger.error(f"Git pull failed: {result.stderr}")

        return result.returncode == 0

    except Exception as e:
        logger.error(f"Git pull exception: {e}")
        return False


def _run_extractor(local_path: str, output_json: str) -> bool:
    try:
        result = subprocess.run(
            ['repository-doc-extractor', local_path, '-o', output_json],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            logger.error(f"Extraction failed: {result.stderr}")

        return result.returncode == 0

    except Exception as e:
        logger.error(f"Extraction exception: {e}")
        return False


def _run_validation(json_file: str) -> bool:
    try:
        result = subprocess.run(
            ['minerva', 'validate', json_file],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            logger.error(f"Validation failed: {result.stderr}")

        return result.returncode == 0

    except Exception as e:
        logger.error(f"Validation exception: {e}")
        return False


def _run_indexing(index_config: str) -> bool:
    try:
        result = subprocess.run(
            ['minerva', 'index', '--config', index_config],
            capture_output=True,
            text=True,
            timeout=600,
            env=os.environ.copy()
        )

        if result.returncode != 0:
            logger.error(f"Indexing failed: {result.stderr}")

        return result.returncode == 0

    except Exception as e:
        logger.error(f"Indexing exception: {e}")
        return False


def _get_extracted_json_path(index_config: str) -> str:
    import json

    with open(index_config, 'r') as f:
        config = json.load(f)

    json_file = config['collection']['json_file']

    json_path = Path(json_file).expanduser()
    if not json_path.is_absolute():
        config_dir = Path(index_config).parent.resolve()
        json_path = config_dir / json_file

    json_path = json_path.resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)

    return str(json_path)

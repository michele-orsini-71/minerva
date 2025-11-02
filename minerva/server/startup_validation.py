import os
import sys
from pathlib import Path
from minerva.common.exceptions import ConfigError, StartupValidationError
from minerva.indexing.storage import initialize_chromadb_client
from minerva.common.logger import get_logger

console_logger = get_logger(__name__, simple=True)


def validate_chromadb_path(chromadb_path: str) -> None:
    if not chromadb_path or not chromadb_path.strip():
        raise StartupValidationError(
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

    path = Path(chromadb_path)
    if not path.exists():
        raise StartupValidationError(
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
            "     minerva index --config config.json\n"
            "     (See minerva --help for more options)\n"
            "\n"
            "  4. Ensure the ChromaDB path in config.json matches where the pipeline\n"
            "     created the database (default: ../chromadb_data)"
        )

    if not path.is_dir():
        raise StartupValidationError(
            f"ChromaDB path is not a directory: {chromadb_path}\n"
            "\n"
            "  The configured path exists but is a file, not a directory.\n"
            "\n"
            "  Remediation steps:\n"
            "  1. Check that the path in config.json points to a directory\n"
            "  2. ChromaDB storage requires a directory to store collections\n"
            "  3. Update config.json with the correct directory path"
        )

    if not os.access(chromadb_path, os.R_OK):
        raise StartupValidationError(
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


def validate_collection_availability(chromadb_path: str) -> None:
    try:
        client = initialize_chromadb_client(chromadb_path)
        collections = client.list_collections()

        if not collections:
            raise StartupValidationError(
                "No collections found in ChromaDB\n"
                "\n"
                "  The ChromaDB database exists but contains no collections.\n"
                "  You need to create at least one collection before using the MCP server.\n"
                "\n"
                "  Remediation steps:\n"
                "  1. Run the RAG pipeline to create a collection from your notes:\n"
                "     minerva index --config config.json --verbose\n"
                "     (See minerva --help for more options)\n"
                "\n"
                "  2. The pipeline will create embeddings and store them in ChromaDB\n"
                "\n"
                "  3. Verify collections were created:\n"
                "     python -c \"import chromadb; client = chromadb.PersistentClient(path='"
                + chromadb_path
                + "'); print([c.name for c in client.list_collections()])\"\n"
                "\n"
                "  4. Restart the MCP server once collections are available"
            )

    except StartupValidationError:
        raise
    except Exception as error:
        raise StartupValidationError(
            "Failed to connect to ChromaDB or list collections\n"
            "\n"
            f"  Error: {error}\n"
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
        ) from error


def validate_server_prerequisites(chromadb_path: str) -> None:
    validate_chromadb_path(chromadb_path)
    validate_collection_availability(chromadb_path)


def main(argv: list[str]) -> None:
    from minerva.common.config_loader import load_unified_config
    from minerva.common.exceptions import ConfigError

    if len(argv) < 2:
        raise StartupValidationError(
            "Configuration path is required.\n"
            "Usage: python -m minerva.server.startup_validation <config.json>"
        )

    config_path = argv[1]

    try:
        unified_config = load_unified_config(config_path)
    except ConfigError as error:
        raise StartupValidationError(str(error)) from error

    console_logger.info("Running server validation checks...\n")
    validate_server_prerequisites(unified_config.server.chromadb_path)
    console_logger.success("✓ All validation checks passed!")
    console_logger.info("\nServer is ready to start.")


if __name__ == "__main__":
    try:
        main(sys.argv)
    except StartupValidationError as error:
        console_logger.error(f"Validation failed:\n\n{error}")
        raise
    except Exception as error:
        console_logger.error(f"Validation error: {error}")
        raise

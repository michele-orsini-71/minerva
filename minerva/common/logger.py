import sys
import logging
from typing import Literal


class ConsoleLogger:
    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def info(self, message: str) -> None:
        self._logger.info(message)

    def success(self, message: str) -> None:
        # For success messages, we use info level in the underlying logger
        self._logger.info(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str, print_to_stderr: bool = True) -> None:
        self._logger.error(message)

        # For fatal errors (e.g., before sys.exit), also print to stderr
        # to ensure visibility even if logging is misconfigured
        if print_to_stderr:
            print(f"\n✗ {message}\n", file=sys.stderr)

    @staticmethod
    def get_logger(
        name: str,
        level: int = logging.INFO,
        mode: Literal["cli", "server"] = "server"
    ) -> 'ConsoleLogger':
        # Get or create Python logger
        python_logger = logging.getLogger(name)

        # Only configure if not already configured (avoid duplicate handlers)
        if not python_logger.handlers:
            python_logger.setLevel(level)

            # CLI mode: stdout for user-facing output
            # Server mode: stderr to avoid contaminating stdio JSON-RPC communication
            output_stream = sys.stdout if mode == "cli" else sys.stderr
            handler = logging.StreamHandler(output_stream)
            handler.setLevel(level)

            # Format: timestamp - module - level - message
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)

            python_logger.addHandler(handler)

            # Disable propagation to root logger to avoid duplicate output
            # (FastMCP adds a RichHandler to the root logger)
            python_logger.propagate = False

        # Wrap in ConsoleLogger and return
        return ConsoleLogger(python_logger)

    @staticmethod
    def create_simple_logger(
        name: str,
        mode: Literal["cli", "server"] = "server"
    ) -> 'ConsoleLogger':
        python_logger = logging.getLogger(name)

        # Only configure if not already configured
        if not python_logger.handlers:
            python_logger.setLevel(logging.INFO)

            # CLI mode: stdout for user-facing output
            # Server mode: stderr to avoid contaminating stdio JSON-RPC communication
            output_stream = sys.stdout if mode == "cli" else sys.stderr
            handler = logging.StreamHandler(output_stream)
            handler.setLevel(logging.INFO)

            # Simple format: just the message
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)

            python_logger.addHandler(handler)

            # Disable propagation to root logger to avoid duplicate output
            # (FastMCP adds a RichHandler to the root logger)
            python_logger.propagate = False

        return ConsoleLogger(python_logger)


# Convenience function for quick logger creation
def get_logger(
    name: str,
    simple: bool = False,
    mode: Literal["cli", "server"] = "server"
) -> ConsoleLogger:
    if simple:
        return ConsoleLogger.create_simple_logger(name, mode=mode)
    return ConsoleLogger.get_logger(name, mode=mode)

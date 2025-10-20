"""
ConsoleLogger - A user-friendly logging facade for CLI commands and MCP server.

This module provides a clean interface for console output that wraps Python's
logging module. It handles formatting, output routing (stdout vs stderr), and
provides semantic methods for different message types.

Design rationale:
- Facade pattern over Python's logging module for simplified API
- Separates user-facing console output from structured debug logging
- Context-aware output routing: stdout for CLI, stderr for MCP server
- Supports both detailed (timestamp + module + level + message) and simple (message only) modes
"""

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
        """
        Create a detailed logger with timestamp, module, level, and message.

        Args:
            name: Logger name (typically __name__)
            level: Logging level (default: INFO)
            mode: Output mode - "cli" routes to stdout, "server" routes to stderr
                  (default: "server" for MCP server compatibility)

        Returns:
            ConsoleLogger instance
        """
        # Get or create Python logger
        python_logger = logging.getLogger(name)

        # Only configure if not already configured (avoid duplicate handlers)
        if not python_logger.handlers:
            python_logger.setLevel(level)

            # Create console handler with context-aware output routing
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
        """
        Create a simple logger with message-only formatting (no timestamp/level).

        Args:
            name: Logger name (typically __name__)
            mode: Output mode - "cli" routes to stdout, "server" routes to stderr
                  (default: "server" for MCP server compatibility)

        Returns:
            ConsoleLogger instance
        """
        python_logger = logging.getLogger(name)

        # Only configure if not already configured
        if not python_logger.handlers:
            python_logger.setLevel(logging.INFO)

            # Create console handler with context-aware output routing
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
    """
    Convenience function for quick logger creation.

    Args:
        name: Logger name (typically __name__)
        simple: If True, creates simple logger (message only), else detailed logger
        mode: Output mode - "cli" routes to stdout, "server" routes to stderr

    Returns:
        ConsoleLogger instance

    Examples:
        # CLI command logger (stdout, detailed)
        logger = get_logger(__name__, mode="cli")

        # CLI command logger (stdout, simple)
        logger = get_logger(__name__, simple=True, mode="cli")

        # MCP server logger (stderr, detailed) - default
        logger = get_logger(__name__)

        # MCP server logger (stderr, simple)
        logger = get_logger(__name__, simple=True)
    """
    if simple:
        return ConsoleLogger.create_simple_logger(name, mode=mode)
    return ConsoleLogger.get_logger(name, mode=mode)

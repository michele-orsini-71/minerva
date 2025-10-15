"""
ConsoleLogger - A user-friendly logging facade for the MCP server.

This module provides a clean interface for console output that wraps Python's
logging module. It handles formatting, output routing (stdout vs stderr), and
provides semantic methods for different message types.

Design rationale:
- Facade pattern over Python's logging module for simplified API
- Separates user-facing console output from structured debug logging
- Supports both CLI and server modes with appropriate formatting
"""

import sys
import logging
from typing import Optional


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
    def get_logger(name: str, level: int = logging.INFO) -> 'ConsoleLogger':
        # Get or create Python logger
        python_logger = logging.getLogger(name)

        # Only configure if not already configured (avoid duplicate handlers)
        if not python_logger.handlers:
            python_logger.setLevel(level)

            # Create console handler with custom formatting
            # IMPORTANT: Use stderr for MCP servers to avoid contaminating stdio JSON-RPC communication
            handler = logging.StreamHandler(sys.stderr)
            handler.setLevel(level)

            # Format: timestamp - module - level - message
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)

            python_logger.addHandler(handler)

        # Wrap in ConsoleLogger and return
        return ConsoleLogger(python_logger)

    @staticmethod
    def create_simple_logger(name: str) -> 'ConsoleLogger':
        python_logger = logging.getLogger(name)

        # Only configure if not already configured
        if not python_logger.handlers:
            python_logger.setLevel(logging.INFO)

            # Create console handler with simple formatting (just the message)
            # IMPORTANT: Use stderr for MCP servers to avoid contaminating stdio JSON-RPC communication
            handler = logging.StreamHandler(sys.stderr)
            handler.setLevel(logging.INFO)

            # Simple format: just the message
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)

            python_logger.addHandler(handler)

        return ConsoleLogger(python_logger)


# Convenience function for quick logger creation
def get_logger(name: str, simple: bool = False) -> ConsoleLogger:
    if simple:
        return ConsoleLogger.create_simple_logger(name)
    return ConsoleLogger.get_logger(name)

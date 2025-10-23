import pytest
import logging
import sys
from io import StringIO
from unittest.mock import patch

from minerva.common.logger import ConsoleLogger, get_logger


class TestConsoleLoggerMethods:
    def test_info_method(self, capsys):
        # Clear existing handlers
        test_logger = logging.getLogger("test.info")
        test_logger.handlers.clear()

        logger = get_logger("test.info", simple=True, mode="cli")
        logger.info("Test info message")

        captured = capsys.readouterr()
        assert "Test info message" in captured.out

    def test_success_method(self, capsys):
        test_logger = logging.getLogger("test.success")
        test_logger.handlers.clear()

        logger = get_logger("test.success", simple=True, mode="cli")
        logger.success("Test success message")

        captured = capsys.readouterr()
        assert "Test success message" in captured.out

    def test_warning_method(self, capsys):
        test_logger = logging.getLogger("test.warning")
        test_logger.handlers.clear()

        logger = get_logger("test.warning", simple=True, mode="cli")
        logger.warning("Test warning message")

        captured = capsys.readouterr()
        assert "Test warning message" in captured.out

    def test_error_method_with_stderr_print(self, capsys):
        test_logger = logging.getLogger("test.error")
        test_logger.handlers.clear()

        logger = get_logger("test.error", simple=True, mode="cli")
        logger.error("Test error message", print_to_stderr=True)

        captured = capsys.readouterr()
        # Should appear in both stdout (via logging) and stderr (via print)
        assert "Test error message" in captured.out
        assert "✗ Test error message" in captured.err

    def test_error_method_without_stderr_print(self, capsys):
        test_logger = logging.getLogger("test.error_no_stderr")
        test_logger.handlers.clear()

        logger = get_logger("test.error_no_stderr", simple=True, mode="cli")
        logger.error("Test error message", print_to_stderr=False)

        captured = capsys.readouterr()
        # Should only appear in stdout (via logging), not in stderr
        assert "Test error message" in captured.out
        assert "✗" not in captured.err


class TestOutputRouting:
    def test_cli_mode_routes_to_stdout(self, capsys):
        # Clear any existing handlers
        test_logger = logging.getLogger("test.cli.stdout")
        test_logger.handlers.clear()

        logger = get_logger("test.cli.stdout", simple=True, mode="cli")
        logger.info("CLI message")

        captured = capsys.readouterr()
        assert "CLI message" in captured.out

    def test_server_mode_routes_to_stderr(self, capsys):
        # Clear any existing handlers
        test_logger = logging.getLogger("test.server.stderr")
        test_logger.handlers.clear()

        logger = get_logger("test.server.stderr", simple=True, mode="server")
        logger.info("Server message")

        captured = capsys.readouterr()
        assert "Server message" in captured.err

    def test_cli_mode_not_in_stderr(self, capsys):
        # Clear any existing handlers
        test_logger = logging.getLogger("test.cli.not.stderr")
        test_logger.handlers.clear()

        logger = get_logger("test.cli.not.stderr", simple=True, mode="cli")
        logger.info("CLI message")

        captured = capsys.readouterr()
        # Should not appear in stderr (except for error messages with print_to_stderr)
        assert "CLI message" not in captured.err

    def test_server_mode_not_in_stdout(self, capsys):
        # Clear any existing handlers
        test_logger = logging.getLogger("test.server.not.stdout")
        test_logger.handlers.clear()

        logger = get_logger("test.server.not.stdout", simple=True, mode="server")
        logger.info("Server message")

        captured = capsys.readouterr()
        assert "Server message" not in captured.out


class TestLoggerFormatting:
    def test_simple_logger_format(self, capsys):
        # Clear any existing handlers
        test_logger = logging.getLogger("test.simple.format")
        test_logger.handlers.clear()

        logger = get_logger("test.simple.format", simple=True, mode="cli")
        logger.info("Simple message")

        captured = capsys.readouterr()
        output = captured.out

        # Simple format should only have message, no timestamp or level
        assert "Simple message" in output
        # Should not contain timestamp pattern (YYYY-MM-DD)
        assert " - " not in output or output.count(" - ") < 2

    def test_detailed_logger_format(self, capsys):
        # Clear any existing handlers
        test_logger = logging.getLogger("test.detailed.format")
        test_logger.handlers.clear()

        logger = get_logger("test.detailed.format", simple=False, mode="cli")
        logger.info("Detailed message")

        captured = capsys.readouterr()
        output = captured.out

        # Detailed format should have timestamp, module, level, and message
        assert "Detailed message" in output
        assert "INFO" in output
        assert "test.detailed.format" in output


class TestGetLoggerFunction:
    def test_get_logger_simple_cli(self):
        logger = get_logger("test.get.simple.cli", simple=True, mode="cli")
        assert isinstance(logger, ConsoleLogger)

    def test_get_logger_detailed_cli(self):
        logger = get_logger("test.get.detailed.cli", simple=False, mode="cli")
        assert isinstance(logger, ConsoleLogger)

    def test_get_logger_simple_server(self):
        logger = get_logger("test.get.simple.server", simple=True, mode="server")
        assert isinstance(logger, ConsoleLogger)

    def test_get_logger_detailed_server(self):
        logger = get_logger("test.get.detailed.server", simple=False, mode="server")
        assert isinstance(logger, ConsoleLogger)

    def test_get_logger_default_is_detailed_server(self, capsys):
        # Clear any existing handlers
        test_logger = logging.getLogger("test.get.default")
        test_logger.handlers.clear()

        logger = get_logger("test.get.default")
        # Default should be detailed (not simple) and server mode (stderr)
        logger.info("Default test")

        captured = capsys.readouterr()
        output = captured.err
        # Should be in stderr and have detailed format
        assert "Default test" in output
        assert "INFO" in output


class TestLoggerConfiguration:
    def test_logger_handlers_not_duplicated(self):
        # Clear any existing handlers
        test_logger = logging.getLogger("test.no.duplicates")
        test_logger.handlers.clear()

        # Create logger twice
        logger1 = get_logger("test.no.duplicates", simple=True, mode="cli")
        logger2 = get_logger("test.no.duplicates", simple=True, mode="cli")

        # Should only have one handler
        python_logger = logging.getLogger("test.no.duplicates")
        assert len(python_logger.handlers) == 1

    def test_logger_propagate_is_false(self):
        # Clear any existing handlers
        test_logger = logging.getLogger("test.no.propagate")
        test_logger.handlers.clear()

        logger = get_logger("test.no.propagate", simple=True, mode="cli")
        python_logger = logging.getLogger("test.no.propagate")

        # Propagate should be False to avoid duplicate output
        assert python_logger.propagate is False

    def test_different_logger_names_get_different_loggers(self):
        logger1 = get_logger("test.logger.one", simple=True, mode="cli")
        logger2 = get_logger("test.logger.two", simple=True, mode="cli")

        # Should be different logger instances
        assert logger1._logger != logger2._logger


class TestConsoleLoggerClass:
    def test_console_logger_wraps_python_logger(self):
        python_logger = logging.getLogger("test.wrapper")
        console_logger = ConsoleLogger(python_logger)

        assert console_logger._logger == python_logger

    def test_get_logger_static_method(self):
        logger = ConsoleLogger.get_logger("test.static.get", mode="cli")
        assert isinstance(logger, ConsoleLogger)

    def test_create_simple_logger_static_method(self):
        logger = ConsoleLogger.create_simple_logger("test.static.simple", mode="cli")
        assert isinstance(logger, ConsoleLogger)


class TestLogLevels:
    def test_info_level_messages(self, capsys):
        # Clear any existing handlers
        test_logger = logging.getLogger("test.levels.info")
        test_logger.handlers.clear()

        logger = get_logger("test.levels.info", simple=False, mode="cli")
        logger.info("Info level")

        captured = capsys.readouterr()
        output = captured.out
        assert "INFO" in output
        assert "Info level" in output

    def test_warning_level_messages(self, capsys):
        # Clear any existing handlers
        test_logger = logging.getLogger("test.levels.warning")
        test_logger.handlers.clear()

        logger = get_logger("test.levels.warning", simple=False, mode="cli")
        logger.warning("Warning level")

        captured = capsys.readouterr()
        output = captured.out
        assert "WARNING" in output
        assert "Warning level" in output

    def test_error_level_messages(self, capsys):
        # Clear any existing handlers
        test_logger = logging.getLogger("test.levels.error")
        test_logger.handlers.clear()

        logger = get_logger("test.levels.error", simple=False, mode="cli")
        logger.error("Error level", print_to_stderr=False)

        captured = capsys.readouterr()
        output = captured.out
        assert "ERROR" in output
        assert "Error level" in output


class TestEdgeCases:
    def test_empty_message(self, capsys):
        logger = get_logger("test.empty", simple=True, mode="cli")
        logger.info("")

        # Should handle empty messages gracefully
        captured = capsys.readouterr()
        output = captured.out
        assert output is not None

    def test_very_long_message(self, capsys):
        logger = get_logger("test.long", simple=True, mode="cli")
        long_message = "A" * 10000
        logger.info(long_message)

        captured = capsys.readouterr()
        output = captured.out
        assert long_message in output

    def test_unicode_message(self, capsys):
        logger = get_logger("test.unicode", simple=True, mode="cli")
        unicode_message = "Test 日本語 🎉 émojis"
        logger.info(unicode_message)

        captured = capsys.readouterr()
        output = captured.out
        assert unicode_message in output

    def test_multiline_message(self, capsys):
        logger = get_logger("test.multiline", simple=True, mode="cli")
        multiline_message = "Line 1\nLine 2\nLine 3"
        logger.info(multiline_message)

        captured = capsys.readouterr()
        output = captured.out
        assert "Line 1" in output
        assert "Line 2" in output
        assert "Line 3" in output

    def test_special_characters_in_message(self, capsys):
        logger = get_logger("test.special", simple=True, mode="cli")
        special_message = "Special: \t\r\n \"quotes\" 'apostrophes' <brackets>"
        logger.info(special_message)

        # Should handle special characters without errors
        captured = capsys.readouterr()
        output = captured.out
        assert "Special" in output


class TestRealWorldUsage:
    def test_cli_command_logger_pattern(self, capsys):
        # Pattern used by CLI commands
        logger = get_logger(__name__, simple=True, mode="cli")
        logger.info("Processing...")
        logger.success("✓ Complete")
        logger.warning("⚠ Warning")

        captured = capsys.readouterr()
        output = captured.out
        assert "Processing..." in output
        assert "✓ Complete" in output
        assert "⚠ Warning" in output

    def test_server_logger_pattern(self, capsys):
        # Pattern used by MCP server
        # Clear any existing handlers
        test_logger = logging.getLogger(__name__)
        test_logger.handlers.clear()

        logger = get_logger(__name__, simple=False, mode="server")
        logger.info("Server starting...")
        logger.info("Server ready")

        captured = capsys.readouterr()
        output = captured.err
        assert "Server starting..." in output
        assert "Server ready" in output
        assert "INFO" in output

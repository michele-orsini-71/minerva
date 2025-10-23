import pytest
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch

from minerva.commands.serve import run_serve


class TestRunServe:
    @patch('minervium.commands.serve.mcp_main')
    def test_serve_successful_start(self, mock_mcp_main, temp_dir: Path):
        config_file = temp_dir / "server-config.json"
        config_file.write_text('{"chromadb_path": "./chromadb_data"}')

        args = Namespace(config=config_file)
        exit_code = run_serve(args)

        assert exit_code == 0
        mock_mcp_main.assert_called_once_with(str(config_file))

    @patch('minervium.commands.serve.mcp_main')
    def test_serve_converts_path_to_string(self, mock_mcp_main, temp_dir: Path):
        config_file = temp_dir / "server-config.json"
        args = Namespace(config=config_file)

        run_serve(args)

        # Verify that the Path was converted to string
        call_args = mock_mcp_main.call_args[0][0]
        assert isinstance(call_args, str)
        assert call_args == str(config_file)

    @patch('minervium.commands.serve.mcp_main')
    def test_serve_handles_keyboard_interrupt(self, mock_mcp_main, temp_dir: Path):
        mock_mcp_main.side_effect = KeyboardInterrupt()

        config_file = temp_dir / "server-config.json"
        args = Namespace(config=config_file)

        exit_code = run_serve(args)

        assert exit_code == 130

    @patch('minervium.commands.serve.mcp_main')
    def test_serve_handles_general_exception(self, mock_mcp_main, temp_dir: Path):
        mock_mcp_main.side_effect = Exception("Server startup failed")

        config_file = temp_dir / "server-config.json"
        args = Namespace(config=config_file)

        exit_code = run_serve(args)

        assert exit_code == 1

    @patch('minervium.commands.serve.mcp_main')
    def test_serve_with_absolute_path(self, mock_mcp_main):
        config_file = Path("/absolute/path/to/server-config.json")
        args = Namespace(config=config_file)

        run_serve(args)

        mock_mcp_main.assert_called_once_with("/absolute/path/to/server-config.json")

    @patch('minervium.commands.serve.mcp_main')
    def test_serve_with_relative_path(self, mock_mcp_main):
        config_file = Path("./configs/server-config.json")
        args = Namespace(config=config_file)

        run_serve(args)

        mock_mcp_main.assert_called_once_with("configs/server-config.json")

    @patch('minervium.commands.serve.mcp_main')
    def test_serve_with_runtime_error(self, mock_mcp_main, temp_dir: Path):
        mock_mcp_main.side_effect = RuntimeError("Failed to bind to port")

        config_file = temp_dir / "server-config.json"
        args = Namespace(config=config_file)

        exit_code = run_serve(args)

        assert exit_code == 1

    @patch('minervium.commands.serve.mcp_main')
    def test_serve_with_value_error(self, mock_mcp_main, temp_dir: Path):
        mock_mcp_main.side_effect = ValueError("Invalid configuration")

        config_file = temp_dir / "server-config.json"
        args = Namespace(config=config_file)

        exit_code = run_serve(args)

        assert exit_code == 1


class TestServeIntegration:
    @patch('minervium.commands.serve.mcp_main')
    def test_serve_blocks_until_completion(self, mock_mcp_main, temp_dir: Path):
        # Simulate server running and then shutting down
        mock_mcp_main.return_value = None

        config_file = temp_dir / "server-config.json"
        args = Namespace(config=config_file)

        exit_code = run_serve(args)

        assert exit_code == 0
        assert mock_mcp_main.called

    @patch('minervium.commands.serve.mcp_main')
    def test_serve_with_unicode_path(self, mock_mcp_main, temp_dir: Path):
        config_file = temp_dir / "サーバー設定.json"
        args = Namespace(config=config_file)

        run_serve(args)

        mock_mcp_main.assert_called_once_with(str(config_file))

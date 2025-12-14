import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from minerva_common.minerva_runner import run_index, run_serve, run_validate


@pytest.fixture
def mock_subprocess_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")
        yield mock_run


@pytest.fixture
def mock_subprocess_failure():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error occurred")
        yield mock_run


def test_run_validate_success(mock_subprocess_success):
    success, output = run_validate("/path/to/notes.json")

    assert success is True
    assert "Success" in output
    mock_subprocess_success.assert_called_once_with(
        ["minerva", "validate", "/path/to/notes.json"],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_run_validate_failure(mock_subprocess_failure):
    success, output = run_validate("/path/to/notes.json")

    assert success is False
    assert "Error occurred" in output


def test_run_validate_with_path_object(mock_subprocess_success):
    success, output = run_validate(Path("/path/to/notes.json"))

    assert success is True
    mock_subprocess_success.assert_called_once()
    args = mock_subprocess_success.call_args[0][0]
    assert args == ["minerva", "validate", "/path/to/notes.json"]


def test_run_validate_timeout():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)

        success, output = run_validate("/path/to/notes.json")

        assert success is False
        assert "timed out" in output.lower()


def test_run_validate_command_not_found():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError()

        success, output = run_validate("/path/to/notes.json")

        assert success is False
        assert "not found" in output.lower()


def test_run_validate_exception():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = Exception("Unexpected error")

        success, output = run_validate("/path/to/notes.json")

        assert success is False
        assert "Unexpected error" in output


def test_run_index_success_verbose(mock_subprocess_success):
    success, output = run_index("/path/to/config.json", verbose=True)

    assert success is True
    mock_subprocess_success.assert_called_once()
    args = mock_subprocess_success.call_args[0][0]
    assert args == ["minerva", "index", "--config", "/path/to/config.json", "--verbose"]


def test_run_index_success_non_verbose(mock_subprocess_success):
    success, output = run_index("/path/to/config.json", verbose=False)

    assert success is True
    assert "Success" in output
    mock_subprocess_success.assert_called_once()
    args = mock_subprocess_success.call_args[0][0]
    assert args == ["minerva", "index", "--config", "/path/to/config.json"]


def test_run_index_failure(mock_subprocess_failure):
    success, output = run_index("/path/to/config.json", verbose=False)

    assert success is False
    assert "Error occurred" in output


def test_run_index_with_path_object(mock_subprocess_success):
    success, output = run_index(Path("/path/to/config.json"), verbose=False)

    assert success is True
    mock_subprocess_success.assert_called_once()
    args = mock_subprocess_success.call_args[0][0]
    assert args == ["minerva", "index", "--config", "/path/to/config.json"]


def test_run_index_custom_timeout(mock_subprocess_success):
    success, output = run_index("/path/to/config.json", timeout=300, verbose=False)

    assert success is True
    mock_subprocess_success.assert_called_once()
    kwargs = mock_subprocess_success.call_args[1]
    assert kwargs["timeout"] == 300


def test_run_index_timeout():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 600)

        success, output = run_index("/path/to/config.json", verbose=False)

        assert success is False
        assert "timed out" in output.lower()
        assert "600" in output


def test_run_index_command_not_found():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = FileNotFoundError()

        success, output = run_index("/path/to/config.json", verbose=False)

        assert success is False
        assert "not found" in output.lower()


def test_run_index_exception():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = Exception("Unexpected error")

        success, output = run_index("/path/to/config.json", verbose=False)

        assert success is False
        assert "Unexpected error" in output


def test_run_serve_returns_process():
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        process = run_serve("/path/to/server.json")

        assert process == mock_process
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args == ["minerva", "serve", "--config", "/path/to/server.json"]


def test_run_serve_with_path_object():
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        process = run_serve(Path("/path/to/server.json"))

        assert process == mock_process
        args = mock_popen.call_args[0][0]
        assert args == ["minerva", "serve", "--config", "/path/to/server.json"]


def test_run_serve_stdout_stderr():
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        run_serve("/path/to/server.json")

        kwargs = mock_popen.call_args[1]
        assert "stdout" in kwargs
        assert "stderr" in kwargs

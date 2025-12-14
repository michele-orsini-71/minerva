import subprocess
import sys
from pathlib import Path


def run_validate(json_file: str | Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["minerva", "validate", str(json_file)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Validation timed out after 30 seconds"
    except FileNotFoundError:
        return False, "minerva command not found. Please ensure minerva is installed."
    except Exception as e:
        return False, f"Error running validation: {str(e)}"


def run_index(config_path: str | Path, timeout: int = 600, verbose: bool = True) -> tuple[bool, str]:
    try:
        cmd = ["minerva", "index", "--config", str(config_path)]
        if verbose:
            cmd.append("--verbose")

        if verbose:
            result = subprocess.run(
                cmd,
                text=True,
                timeout=timeout,
            )
            return result.returncode == 0, ""
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode == 0, result.stdout + result.stderr

    except subprocess.TimeoutExpired:
        return False, f"Indexing timed out after {timeout} seconds"
    except FileNotFoundError:
        return False, "minerva command not found. Please ensure minerva is installed."
    except Exception as e:
        return False, f"Error running indexing: {str(e)}"


def run_serve(server_config_path: str | Path) -> subprocess.Popen:
    cmd = ["minerva", "serve", "--config", str(server_config_path)]

    process = subprocess.Popen(
        cmd,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    return process

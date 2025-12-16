import subprocess
import sys
import shutil
from pathlib import Path


def _get_minerva_command() -> str:
    """Get the full path to the minerva command.

    Checks common installation locations since PATH may not be available
    (e.g., when running from Claude Desktop MCP).
    """
    import os

    # Try using PATH first (works in normal shell)
    minerva_path = shutil.which("minerva")
    if minerva_path and os.path.exists(minerva_path):
        return minerva_path

    # Common installation locations (when PATH is not available)
    home = Path.home()
    common_locations = [
        home / ".local" / "bin" / "minerva",  # pipx default
        Path("/usr/local/bin/minerva"),       # system install
        Path("/usr/bin/minerva"),              # system install
    ]

    for location in common_locations:
        if location.exists():
            return str(location)

    raise FileNotFoundError(
        "minerva command not found. Tried:\n"
        f"  - PATH search\n"
        f"  - {common_locations[0]}\n"
        f"  - {common_locations[1]}\n"
        f"  - {common_locations[2]}\n"
        "Please ensure minerva is installed: pipx install minerva"
    )


def run_validate(json_file: str | Path) -> tuple[bool, str]:
    try:
        minerva_cmd = _get_minerva_command()
        result = subprocess.run(
            [minerva_cmd, "validate", str(json_file)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Validation timed out after 30 seconds"
    except FileNotFoundError as e:
        return False, f"minerva command not found: {e}"
    except Exception as e:
        return False, f"Error running validation: {str(e)}"


def run_index(config_path: str | Path, timeout: int = 600, verbose: bool = True) -> tuple[bool, str]:
    try:
        minerva_cmd = _get_minerva_command()
        cmd = [minerva_cmd, "index", "--config", str(config_path)]
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
    except FileNotFoundError as e:
        return False, f"minerva command not found: {e}"
    except Exception as e:
        return False, f"Error running indexing: {str(e)}"


def run_serve(server_config_path: str | Path) -> subprocess.Popen:
    minerva_cmd = _get_minerva_command()
    cmd = [minerva_cmd, "serve", "--config", str(server_config_path)]

    process = subprocess.Popen(
        cmd,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    return process

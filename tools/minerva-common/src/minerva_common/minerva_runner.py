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


def run_index(config_path: str | Path, timeout: int = 60, verbose: bool = True) -> tuple[bool, str]:
    import select
    import time

    try:
        minerva_cmd = _get_minerva_command()
        cmd = [minerva_cmd, "index", "--config", str(config_path)]
        if verbose:
            cmd.append("--verbose")

        # Use Popen for real-time output monitoring
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE if not verbose else None,
            stderr=subprocess.PIPE if not verbose else None,
            text=True,
        )

        if verbose:
            # In verbose mode, output goes directly to stdout/stderr
            # Just wait for completion with no timeout (Ctrl+C works)
            returncode = process.wait()
            return returncode == 0, ""
        else:
            # In non-verbose mode, capture output and monitor for activity
            output_lines = []
            last_output_time = time.time()

            while True:
                # Check if process has finished
                returncode = process.poll()
                if returncode is not None:
                    # Process finished, collect remaining output
                    remaining_stdout, remaining_stderr = process.communicate()
                    if remaining_stdout:
                        output_lines.append(remaining_stdout)
                    if remaining_stderr:
                        output_lines.append(remaining_stderr)
                    return returncode == 0, "".join(output_lines)

                # Check for timeout (no output for X seconds)
                if time.time() - last_output_time > timeout:
                    process.kill()
                    process.wait()
                    return False, (
                        f"Indexing timed out: no output for {timeout} seconds\n"
                        f"Process may be stuck. Last output:\n" +
                        "".join(output_lines[-10:]) if output_lines else "(no output)"
                    )

                # Read available output (non-blocking)
                # Note: This is a simplified version. For production, consider using
                # threading or asyncio for proper non-blocking I/O
                try:
                    stdout_line = process.stdout.readline()
                    if stdout_line:
                        output_lines.append(stdout_line)
                        last_output_time = time.time()
                        continue
                except:
                    pass

                try:
                    stderr_line = process.stderr.readline()
                    if stderr_line:
                        output_lines.append(stderr_line)
                        last_output_time = time.time()
                        continue
                except:
                    pass

                # Small sleep to avoid busy-waiting
                time.sleep(0.1)

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

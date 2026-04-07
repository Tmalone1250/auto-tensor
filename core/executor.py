"""
core/executor.py — WSL Mandate Enforcer
All shell commands MUST execute via wsl.exe / WSL bash.
Includes path sanitization for Windows → Linux path conversion.
"""
import subprocess
import logging
import os
import re
from typing import Optional

LOG_PATH = "logs/executor.log"
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


# ---------------------------------------------------------------------------
# Path Sanitization
# ---------------------------------------------------------------------------

def win_to_wsl(path: str) -> str:
    """
    Convert a Windows-style path to a WSL Linux path.

    Examples:
        C:\\Users\\malon\\workspace  →  /mnt/c/Users/malon/workspace
        C:/Users/malon/workspace    →  /mnt/c/Users/malon/workspace
    """
    path = path.replace("\\", "/")
    # Match drive letter at the start (e.g. C:/)
    match = re.match(r"^([A-Za-z]):/(.*)$", path)
    if match:
        drive = match.group(1).lower()
        rest  = match.group(2)
        return f"/mnt/{drive}/{rest}"
    return path  # Already a Linux-style path; return as-is


def sanitize_workspace_path(path: str) -> str:
    """Ensure any path inside /workspace is WSL-safe."""
    return win_to_wsl(path)


# ---------------------------------------------------------------------------
# WSL Executor
# ---------------------------------------------------------------------------

def run_wsl(
    command: str,
    cwd: Optional[str] = None,
    capture: bool = True,
    timeout: int = 300,
) -> subprocess.CompletedProcess:
    """
    Execute a shell command inside WSL bash.

    Args:
        command:  The bash command string to run.
        cwd:      Optional working directory (Windows OR Linux path — auto-converted).
        capture:  Whether to capture stdout/stderr.
        timeout:  Max seconds to wait.

    Returns:
        subprocess.CompletedProcess with returncode, stdout, stderr.
    """
    wsl_cwd = win_to_wsl(cwd) if cwd else None

    if wsl_cwd:
        full_command = f'cd "{wsl_cwd}" && {command}'
    else:
        full_command = command

    wsl_args = ["wsl", "bash", "-c", full_command]

    logging.info(f"WSL EXEC: {full_command}")
    print(f"[EXECUTOR] WSL > {full_command}")

    try:
        result = subprocess.run(
            wsl_args,
            capture_output=capture,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            logging.info(f"WSL SUCCESS (exit 0): {command[:80]}")
        else:
            logging.warning(
                f"WSL FAILURE (exit {result.returncode}): {command[:80]}\n"
                f"stderr: {result.stderr[:500]}"
            )
        return result
    except subprocess.TimeoutExpired:
        logging.error(f"WSL TIMEOUT after {timeout}s: {command[:80]}")
        raise
    except Exception as e:
        logging.error(f"WSL EXEC ERROR: {e}")
        raise


def run_wsl_in_workspace(repo_subpath: str, command: str, **kwargs) -> subprocess.CompletedProcess:
    """
    Convenience wrapper: run a command in a /workspace subdirectory.
    repo_subpath example: 'optimism/rust/kona'
    """
    base_workspace = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "workspace",
    )
    cwd = os.path.join(base_workspace, repo_subpath.replace("/", os.sep))
    return run_wsl(command, cwd=cwd, **kwargs)


# ---------------------------------------------------------------------------
# CLI Smoke-Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Test path sanitization
    win_path = r"C:\Users\malon\Web2 Development\Auto-Tensor\workspace\optimism"
    print(f"Win → WSL: {win_to_wsl(win_path)}")

    # Test WSL execution
    result = run_wsl("echo 'WSL Mandate: ACTIVE' && go version && just --version")
    print(result.stdout)
    if result.returncode != 0:
        print(f"[EXECUTOR] stderr: {result.stderr}")

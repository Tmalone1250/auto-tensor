"""
core/executor.py — WSL Mandate Enforcer
All shell commands MUST execute via wsl.exe / WSL bash.
Includes path sanitization for Windows → Linux path conversion.
"""
import subprocess
import logging
import os
import re
import platform
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
    """Ensure any path inside /workspace is shell-safe for the host OS."""
    if platform.system() == "Windows":
        return win_to_wsl(path)
    return path


# ---------------------------------------------------------------------------
# WSL Executor
# ---------------------------------------------------------------------------

def run_bootstrap(cwd: str, marker: str) -> None:
    """Detects and installs dependencies for the target workspace."""
    if not cwd or not os.path.exists(cwd):
        return

    # 1. Python (pyproject.toml or requirements.txt)
    if os.path.exists(os.path.join(cwd, "pyproject.toml")) or os.path.exists(os.path.join(cwd, "requirements.txt")):
        cmd = "python3 -m pip install -e . || python3 -m pip install -r requirements.txt"
        logging.info(f"{marker} BOOTSTRAP: Detected Python. Installing deps...")
        print(f"[EXECUTOR] {marker} > BOOTSTRAP (Python) -> {cmd}")
        subprocess.run(["bash", "-c", f'cd "{cwd}" && {cmd}'], capture_output=True)
        return

    # 2. Node.js (package.json)
    if os.path.exists(os.path.join(cwd, "package.json")):
        cmd = "npm install"
        logging.info(f"{marker} BOOTSTRAP: Detected Node.js. Running npm install...")
        print(f"[EXECUTOR] {marker} > BOOTSTRAP (Node.js) -> {cmd}")
        subprocess.run(["bash", "-c", f'cd "{cwd}" && {cmd}'], capture_output=True)
        return

    # 3. Rust (Cargo.toml)
    if os.path.exists(os.path.join(cwd, "Cargo.toml")):
        cmd = "cargo build"
        logging.info(f"{marker} BOOTSTRAP: Detected Rust. Running cargo build...")
        print(f"[EXECUTOR] {marker} > BOOTSTRAP (Rust) -> {cmd}")
        subprocess.run(["bash", "-c", f'cd "{cwd}" && {cmd}'], capture_output=True)
        return

def run_wsl(
    command: str,
    cwd: Optional[str] = None,
    capture: bool = True,
    timeout: int = 300,
    bootstrap: bool = True
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
    # 1. OS-Aware Path Sanitization
    is_linux = platform.system() == "Linux"
    shell_cwd = win_to_wsl(cwd) if (cwd and not is_linux) else cwd

    # 1b. TTY Spoofing: Force narrow columns for TUI reproduction
    tty_suffix = "export COLUMNS=40; export LINES=24; "
    
    if shell_cwd:
        full_command = f'cd "{shell_cwd}" && {tty_suffix}{command}'
    else:
        full_command = f"{tty_suffix}{command}"

    # 2. Command Prefixing
    if is_linux:
        shell_args = ["bash", "-c", full_command]
        marker = "NATIVE"
    else:
        shell_args = ["wsl", "bash", "-c", full_command]
        marker = "WSL"

    # 3. Dynamic Bootstrap (Only once per mission if possible, or per start)
    if bootstrap and cwd:
        run_bootstrap(cwd, marker)

    logging.info(f"{marker} EXEC: {full_command}")
    print(f"[EXECUTOR] {marker} > {full_command}")

    try:
        result = subprocess.run(
            shell_args,
            capture_output=capture,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            logging.info(f"{marker} SUCCESS (exit 0): {command[:80]}")
        else:
            logging.warning(
                f"{marker} FAILURE (exit {result.returncode}): {command[:80]}\n"
                f"stderr: {result.stderr[:500]}"
            )
        return result
    except subprocess.TimeoutExpired:
        logging.error(f"{marker} TIMEOUT after {timeout}s: {command[:80]}")
        raise
    except Exception as e:
        logging.error(f"{marker} EXEC ERROR: {e}")
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

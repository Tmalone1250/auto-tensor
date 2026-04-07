"""
agents/coder.py — Coder Agent v1.0
Surgical Fix Orchestrator for Auto-Tensor.
Governed by core/health_check.py and routes all shell commands via core/executor.py.
"""
import os
import sys
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.health_check import governor_gate
from core.executor import run_wsl_in_workspace, win_to_wsl

LOG_PATH = "logs/coder.log"
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

REPO_SUBPATH = "optimism/rust/kona"
TARGET_SPEC   = "kona/docker/cannon/mips64-unknown-none.json"
IMAGE         = "us-docker.pkg.dev/oplabs-tools-artifacts/images/cannon-builder:v1.0.0"


def reproduce_before(log_path: str) -> str:
    """Run the UNFIXED build to capture the 'Before' error log."""
    logging.info("Coder: Reproducing BEFORE state (unpatched justfile).")
    result = run_wsl_in_workspace(
        REPO_SUBPATH,
        f"docker.exe run --rm "
        f"-v \"$(wslpath -w $(pwd)):/workdir\" "
        f"-w=/workdir {IMAGE} "
        f"cargo build -Zbuild-std=core,alloc -Zjson-target-spec "
        f"-p kona-client --bin kona-client --profile release-client-lto",
        timeout=600,
    )
    before_log = result.stderr or result.stdout
    with open(log_path, "w") as f:
        f.write(before_log)
    return before_log


def reproduce_after(log_path: str) -> tuple[bool, str]:
    """Run the FIXED build to capture the 'After' success log."""
    logging.info("Coder: Running AFTER state (with --target override).")
    result = run_wsl_in_workspace(
        REPO_SUBPATH,
        f"docker.exe run --rm "
        f"-v \"$(wslpath -w $(pwd)):/workdir\" "
        f"-w=/workdir {IMAGE} "
        f"cargo build -Zbuild-std=core,alloc -Zjson-target-spec "
        f"--target {TARGET_SPEC} "
        f"-p kona-client --bin kona-client --profile release-client-lto",
        timeout=600,
    )
    after_log = result.stdout + result.stderr
    with open(log_path, "w") as f:
        f.write(after_log)
    return result.returncode == 0, after_log


def run():
    print("[CODER] Checking Governor clearance...")
    if not governor_gate():
        print("[CODER] Governor BLOCKED — Miner has priority. Halting.")
        return

    print("[CODER] Governor cleared. Beginning reproduction sequence.")

    before_log = reproduce_before("logs/before_build.log")
    success, after_log = reproduce_after("logs/after_build.log")

    status = "SUCCESS" if success else "FAILED"
    print(f"[CODER] Reproduction complete. After-state: {status}")
    logging.info(f"Coder: Reproduction complete. After-state: {status}")

    return {"before": before_log[:500], "after": after_log[:500], "success": success}


if __name__ == "__main__":
    run()

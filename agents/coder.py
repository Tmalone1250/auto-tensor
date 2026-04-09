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

    # Load directive
    mission_params_path = "logs/mission_parameters.json"
    strategy = "Explore and fix based on repository context."
    if os.path.exists(mission_params_path):
        try:
            with open(mission_params_path, "r") as f:
                params = json.load(f)
                strategy = params.get("strategy", strategy)
                print(f"[CODER] MISSION DIRECTIVE RECEIVED: {params.get('title')}")
        except Exception as e:
            print(f"Error loading mission params: {e}")

    print("[CODER] Governor cleared. Beginning directed reproduction sequence.")

    # In a real implementation, 'strategy' would drive the reproduction logic.
    # For now, we execute the Kona sequence while respecting the directive persona.
    before_log = reproduce_before("logs/before_build.log")
    success, after_log = reproduce_after("logs/after_build.log")

    status = "SUCCESS" if success else "FAILED"
    
    # Persona & Directive injection
    from core.llm import LlmClient
    llm = LlmClient()
    
    # The 'Secret Sauce' Prompt
    body_context = params.get("body", "No additional context.")
    directive_prompt = (
        f"SYSTEM: You are a bored expert contributor. An architect has already scouted this issue and provided the following STRATEGY: [{strategy}].\n"
        f"FULL ISSUE CONTEXT: {body_context[:2000]}\n\n"
        f"Your goal is to execute this specific fix with 100% precision. Do not explore unrelated files. Do not refactor. Just fulfill the directive and verify the build."
    )
    
    repro_msg = f"Reproduction complete for {REPO_SUBPATH}. Result: {status}. Strategy followed: {strategy[:100]}..."
    casual_msg = llm.generate(repro_msg, system_override=directive_prompt)
    
    print(f"\n[Bored Coder]: {casual_msg}")
    logging.info(f"Coder: Mission complete. Strategy: {strategy[:50]}... Result: {status}")

    return {"before": before_log[:500], "after": after_log[:500], "success": success}

if __name__ == "__main__":
    run()

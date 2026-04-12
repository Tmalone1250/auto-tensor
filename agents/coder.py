"""
agents/coder.py — Directive-Driven Coder Agent
Surgical Fix Orchestrator that follows standardized Intelligence Handoffs.
Governed by core/health_check.py and executes via core/executor.py.
"""
import os
import sys
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.health_check import governor_gate
from core.executor import run_wsl_in_workspace
from core.llm import LlmClient

# --- Configuration ---
LOG_DIR = "logs"
MAIN_LOG = os.path.join(LOG_DIR, "coder.log")
MISSION_PARAMS = os.path.join(LOG_DIR, "mission_parameters.json")

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=MAIN_LOG,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

import argparse

# --- Global Force Mode ---
FORCE_MODE = False

def log_and_print(msg: str, level: str = "info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    display_msg = f"[{timestamp}] [CODER] {msg}"
    print(display_msg)
    if level == "info":
        logging.info(msg)
    elif level == "error":
        logging.error(msg)
    elif level == "warning":
        logging.warning(msg)

def run_step(mission_id: str, repo: str, command: str, step_name: str) -> str:
    """Executes a command inside the target repo with Governor oversight."""
    log_and_print(f"Checking Governor clearance for {step_name}...")
    if not governor_gate(force=FORCE_MODE):
        log_and_print("Governor BLOCKED — Miner has priority. Waiting for clearance...", "warning")
        # In a real environment, we might sleep and retry, but here we exit to respect priority
        sys.exit(0)

    log_and_print(f"Executing {step_name} in {repo}...")
    result = run_wsl_in_workspace(repo, command, timeout=600)
    
    log_content = result.stdout + result.stderr
    log_file = os.path.join(LOG_DIR, f"{step_name.lower()}_{mission_id}.log")
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(log_content)
    
    status = "SUCCESS" if result.returncode == 0 else "FAILED"
    log_and_print(f"{step_name} finished: {status}")
    return log_content

def execute_mission():
    """Main lifecycle for Directive-Driven Orchestration."""
    parser = argparse.ArgumentParser(description="Auto-Tensor Coder Agent")
    parser.add_argument("--force", action="store_true", help="Bypass Governor safety gates")
    args = parser.parse_args()
    
    global FORCE_MODE
    FORCE_MODE = args.force
    
    if FORCE_MODE:
        log_and_print("FORCE MODE ENABLED: Safety gates bypassed.", "warning")

    log_and_print("--- STARTING CODER MISSION ---")
    
    if not os.path.exists(MISSION_PARAMS):
        log_and_print("Waiting for orders... (mission_parameters.json NOT FOUND)", "warning")
        return

    try:
        with open(MISSION_PARAMS, "r", encoding="utf-8") as f:
            params: Dict[str, Any] = json.load(f)
    except Exception as e:
        log_and_print(f"CRITICAL: Failed to parse mission parameters: {e}", "error")
        return

    mission_id = params.get("mission_id", "UNTITLED")
    target_repo = params.get("target_repo")
    strategy = params.get("strategy")
    repro_cmd = params.get("repro_cmd")
    fix_cmd = params.get("fix_cmd")

    # Guard: Missing critical fields
    if not all([target_repo, repro_cmd, fix_cmd]):
        log_and_print(f"CRITICAL: Mission {mission_id} is malformed. Missing repo/cmds.", "error")
        return

    log_and_print(f"MISSION LOADED: {mission_id} ({params.get('title', 'No Title')})")
    log_and_print(f"STRATEGY: {strategy}")

    # 1. Reproduce BEFORE
    before_log = run_step(mission_id, target_repo, repro_cmd, "BEFORE")
    
    # 2. Execute FIX
    after_log = run_step(mission_id, target_repo, fix_cmd, "AFTER")

    # 3. Final Bored Review
    generate_bored_report(params, before_log, after_log)

def generate_bored_report(params: Dict[str, Any], before: str, after: str):
    """Generates the 'Bored Expert' delta report."""
    llm = LlmClient()
    
    mission_id = params.get("mission_id")
    strategy = params.get("strategy")
    
    system_prompt = (
        "You are a senior systems engineer and an Elite, Bored Contributor. "
        "Your only interest is the DELTA between 'Before' logs (failures) and 'After' logs (fixes/scars). "
        "Keep it highly technical, cynical, and brief. Avoid fluff like 'Hello' or 'I hope this helps'. "
        "Focus on whether the build actually succeeded or why it's still bleeding."
    )
    
    prompt = (
        f"MISSION: {mission_id}\n"
        f"STRATEGY: {strategy}\n\n"
        f"--- BEFORE LOG (FAIL) ---\n{before[-1500:]}\n\n"
        f"--- AFTER LOG (RESULT) ---\n{after[-1500:]}\n\n"
        f"Task: Review the delta and provide a closing remark on the mission success."
    )

    report = llm.generate(prompt, system_override=system_prompt)
    print(f"\n[Bored Coder]:\n{report}\n")
    log_and_print(f"Mission {mission_id} review complete.")

if __name__ == "__main__":
    execute_mission()

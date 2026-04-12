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
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.health_check import governor_gate
from core.executor import run_wsl_in_workspace
from core.llm import LlmClient
# --- Configuration ---
LOG_DIR = "logs"
MAIN_LOG = f"{LOG_DIR}/coder.log"
MISSION_PARAMS = f"{LOG_DIR}/mission_parameters.json"

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
    # Explicit status marker for dashboard
    log_and_print(f"PROGRESS: Starting {step_name} phase...")
    
    result = run_wsl_in_workspace(repo, command, timeout=600)
    
    log_content = result.stdout + result.stderr
    log_file = f"{LOG_DIR}/{step_name.lower()}_{mission_id}.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(log_content)
    
    status = "SUCCESS" if result.returncode == 0 else "FAILED"
    log_and_print(f"{step_name} finished: {status}")
    return log_content

import subprocess

def get_repo_folder(target_repo: str) -> str:
    """Extracts the folder name from a URL or org/repo string."""
    if not target_repo:
        return ""
    # Remove .git and trailing slashes
    clean = target_repo.rstrip("/").replace(".git", "")
    if "/" in clean:
        return clean.split("/")[-1]
    return clean

def fork_repository(target_repo_url: str) -> Optional[str]:
    """Forks the target repository to the authenticated user's account."""
    token = os.getenv("GITHUB_KEY")
    if not token:
        log_and_print("CRITICAL: GITHUB_KEY not found. Cannot fork.", "error")
        return None

    # Parse owner and repo from URL
    parts = target_repo_url.rstrip("/").split("/")
    owner, repo = parts[-2], parts[-1].replace(".git", "")
    
    log_and_print(f"PROGRESS: [Forking Repository {owner}/{repo}...]")
    url = f"https://api.github.com/repos/{owner}/{repo}/forks"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }
    
    try:
        response = requests.post(url, headers=headers, timeout=30)
        if response.status_code in [201, 202]:
            fork_data = response.json()
            fork_url = fork_data.get("html_url")
            log_and_print(f"Fork initiated: {fork_url}")
            # Give GitHub a moment to provision the fork
            time.sleep(5)
            return fork_url
        else:
            log_and_print(f"Failed to fork: {response.status_code} - {response.text}", "error")
            return None
    except Exception as e:
        log_and_print(f"Exception during fork: {e}", "error")
        return None

def create_branch(fork_url: str, mission_id: str) -> Optional[str]:
    """Creates a unique fix branch on the fork."""
    token = os.getenv("GITHUB_KEY")
    parts = fork_url.rstrip("/").split("/")
    owner, repo = parts[-2], parts[-1].replace(".git", "")
    branch_name = f"auto-fix-{mission_id}"
    
    log_and_print(f"PROGRESS: [Creating Branch {branch_name} on {owner}/{repo}...]")
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }

    try:
        # 1. Get default branch and its SHA
        repo_info_url = f"https://api.github.com/repos/{owner}/{repo}"
        repo_info = requests.get(repo_info_url, headers=headers).json()
        default_branch = repo_info.get("default_branch", "main")
        
        ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{default_branch}"
        ref_data = requests.get(ref_url, headers=headers).json()
        base_sha = ref_data.get("object", {}).get("sha")
        
        if not base_sha:
            log_and_print(f"Could not find SHA for {default_branch}", "error")
            return None

        # 2. Create the new branch
        create_ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
        payload = {
            "ref": f"refs/heads/{branch_name}",
            "sha": base_sha
        }
        res = requests.post(create_ref_url, headers=headers, json=payload)
        if res.status_code == 201:
            log_and_print(f"Branch created: {branch_name}")
            return branch_name
        else:
            log_and_print(f"Failed to create branch: {res.status_code} - {res.text}", "error")
            return None
    except Exception as e:
        log_and_print(f"Exception during branching: {e}", "error")
        return None

def ensure_repo_locally(target_repo: str, mission_id: str) -> str:
    """Ensures a forked and branched version of the repo exists in the workspace."""
    folder = get_repo_folder(target_repo)
    workspace_path = f"workspace/{folder}"
    
    # In the professional forking workflow, we always prefer a fresh clone of the branch
    # But if it exists, we assume it's the right one for now.
    if os.path.exists(workspace_path):
        log_and_print(f"Workspace folder '{folder}' already exists. Reusing.")
        return folder

    if not target_repo.startswith("http"):
        log_and_print(f"CRITICAL: Repo '{target_repo}' missing and no URL provided.", "error")
        return ""

    github_token = os.getenv("GITHUB_KEY")
    
    # 1. Fork
    fork_url = fork_repository(target_repo)
    if not fork_url:
        return ""
        
    # 2. Branch
    branch_name = create_branch(fork_url, mission_id)
    if not branch_name:
        return ""

    # 3. Clone Fork's Branch
    log_and_print("PROGRESS: [Cloning Forked Branch...]")
    os.makedirs("workspace", exist_ok=True)
    
    auth_clone_url = fork_url.replace("https://github.com/", f"https://{github_token}@github.com/")
    
    try:
        log_and_print(f"Executing: git clone -b {branch_name} {fork_url} workspace/{folder}")
        # Capture output to prevent token leakage
        subprocess.run(["git", "clone", "-b", branch_name, auth_clone_url, workspace_path], 
                       check=True, capture_output=True, text=True)
        log_and_print(f"Successfully cloned branch {branch_name} of {folder}.")
        return folder
    except subprocess.CalledProcessError as e:
        clean_error = str(e.stderr).replace(github_token, "********") if github_token else e.stderr
        log_and_print(f"CRITICAL: Failed to clone {folder}: {clean_error}", "error")
        return ""
    except Exception as e:
        log_and_print(f"CRITICAL: Unexpected error during clone of {folder}: {e}", "error")
        return ""

def execute_mission():
    """Main lifecycle for Directive-Driven Orchestration."""
    # Move logging initialization to the very first line of mission
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        filename=MAIN_LOG,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    
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
    target_repo_raw = params.get("target_repo") or params.get("repo")
    strategy = params.get("strategy")
    
    # Resilient command extraction with defaults
    repro_cmd = params.get("repro_cmd")
    fix_cmd = params.get("fix_cmd")
    
    # Check for placeholders or missing commands
    if not repro_cmd or "offline" in repro_cmd.lower() or "retry" in repro_cmd.lower():
        repro_cmd = "ls -R"
        log_and_print("Using default reproduction command: ls -R (Sanity check)", "warning")

    if not fix_cmd or "offline" in fix_cmd.lower() or "retry" in fix_cmd.lower():
        fix_cmd = "ls -R"
        log_and_print("Using default fix-verification command: ls -R", "warning")

    # Ensure repository folder exists
    repo_folder = ensure_repo_locally(target_repo_raw, mission_id)
    if not repo_folder:
        log_and_print(f"CRITICAL: Mission {mission_id} aborted — Repository unavailable.", "error")
        return

    log_and_print(f"MISSION LOADED: {mission_id} ({params.get('title', 'No Title')})")
    log_and_print(f"STRATEGY: {strategy}")

    # 1. Reproduce BEFORE
    before_log = run_step(mission_id, repo_folder, repro_cmd, "BEFORE")
    
    # 2. Execute FIX
    after_log = run_step(mission_id, repo_folder, fix_cmd, "AFTER")

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

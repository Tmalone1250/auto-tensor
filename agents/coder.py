import os
import sys
import json
import logging
import subprocess
from core.base_agent import BaseAgent
from core.tools.common import reflect_and_memorize

LOG_DIR = "logs"
MAIN_LOG = f"{LOG_DIR}/coder.log"
MISSION_PARAMS = f"{LOG_DIR}/current_mission.json" # Derived directly from the active promotion pipeline
DIFF_PATH = f"{LOG_DIR}/coder_diff.md"

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(filename=MAIN_LOG, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def log_and_print(msg: str):
    print(f"[CODER] {msg}")
    logging.info(msg)

class CoderAgent(BaseAgent):
    def __init__(self):
        super().__init__("coder")

    def spin_mission(self):
        log_and_print("--- STARTING CODER MISSION (V3 PIPELINE) ---")
        
        if not os.path.exists(MISSION_PARAMS):
            log_and_print("Waiting for orders... (current_mission.json NOT FOUND)")
            return

        with open(MISSION_PARAMS, "r", encoding="utf-8") as f:
            params = json.load(f)

        target_repo = params.get("repo", "").split("/")[-1].replace(".git", "")
        repro_cmd = params.get("repro_cmd", "ls -R")
        fix_cmd = params.get("fix_cmd", "ls -R")
        strategy = params.get("strategy", "No strategy listed.")

        # Ensure native tool utilization within context parameter
        context = (f"Target Repository: {target_repo}\n"
                   f"Strategy: {strategy}\n"
                   f"Reproduction Cmd: {repro_cmd}\n"
                   f"Verification Cmd: {fix_cmd}\n\n"
                   f"Goal: Iterate over files safely using tools to implement the patch strategy. Output FINISH when Verification Cmd passes. Ensure FINISH returns args mapping to: target_repo, entry_point, and fix_cmd.")
        
        # Start Heartbeat Iteration
        self.execute_mission(context)

        # Generate Active Diff mapping to workspace limits
        log_and_print("Generating Git Diffs...")
        workspace_path = os.path.join("workspace", target_repo)
        if os.path.exists(workspace_path):
            try:
                diff_res = subprocess.run(["git", "diff"], cwd=workspace_path, capture_output=True, text=True)
                diff_data = diff_res.stdout if diff_res.stdout else "No unstaged changes detected."
                
                with open(DIFF_PATH, "w", encoding="utf-8") as f:
                    f.write(f"```diff\n{diff_data}\n```")
                log_and_print(f"Diff successfully exported to {DIFF_PATH}.")
            except Exception as e:
                log_and_print(f"Failed to generate diff natively: {str(e)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", help="Target repository")
    args = parser.parse_args()
    
    agent = CoderAgent()
    agent.spin_mission()

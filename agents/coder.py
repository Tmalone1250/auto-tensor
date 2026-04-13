import os
import sys
import json
import logging
from core.base_agent import BaseAgent
from core.tools.common import execute_mission_step, reflect_and_memorize

LOG_DIR = "logs"
MAIN_LOG = f"{LOG_DIR}/coder.log"
MISSION_PARAMS = f"{LOG_DIR}/mission_parameters.json"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(filename=MAIN_LOG, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def log_and_print(msg: str):
    print(f"[CODER] {msg}")
    logging.info(msg)

class CoderAgent(BaseAgent):
    def __init__(self):
        super().__init__("coder")

    def execute_mission(self):
        log_and_print("--- STARTING CODER MISSION (V3 PIPELINE) ---")
        if not os.path.exists(MISSION_PARAMS):
            log_and_print("Waiting for orders... (mission_parameters.json NOT FOUND)")
            return

        with open(MISSION_PARAMS, "r", encoding="utf-8") as f:
            params = json.load(f)

        target_repo = params.get("target_repo", "").split("/")[-1].replace(".git", "")
        repro_cmd = params.get("repro_cmd", "ls -R")
        fix_cmd = params.get("fix_cmd", "ls -R")
        strategy = params.get("strategy", "")
        entry_point = params.get("entry_point", "UNKNOWN")

        # Execute BEFORE safely bypassing bash abstractions natively
        log_and_print(f"Executing BEFORE phase on {target_repo}...")
        before_log = execute_mission_step(target_repo, repro_cmd)

        # Route intelligence deterministically based on tool signal
        state = "SUCCESS" if "Error" not in before_log and "Exception" not in before_log else "CRITICAL_FAILURE"
        self.route(f"BEFORE Command output:\n{before_log[-1000:]}", state)

        # Execute AFTER securely
        log_and_print(f"Executing AFTER phase on {target_repo}...")
        after_log = execute_mission_step(target_repo, fix_cmd)

        # Re-eval state
        state = "SUCCESS" if "Error" not in after_log and "Exception" not in after_log else "CRITICAL_FAILURE"
        self.route(f"AFTER Command output:\n{after_log[-1000:]}", state)

        # The Reflection Mandate (V3 Requirement)
        log_and_print("Triggering Reflection Mandate...")
        result_msg = "SUCCESS" if state == "SUCCESS" else "FAILURE"
        reflect_msg = reflect_and_memorize("coder", target_repo, entry_point, fix_cmd)
        log_and_print(reflect_msg)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", help="Target repository")
    args = parser.parse_args()
    
    agent = CoderAgent()
    agent.execute_mission()

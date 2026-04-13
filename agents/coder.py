import os
import sys
import json
import logging
from core.base_agent import BaseAgent

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

    def spin_mission(self):
        log_and_print("--- STARTING CODER MISSION (V3 HEARTBEAT) ---")
        if not os.path.exists(MISSION_PARAMS):
            log_and_print("Waiting for orders... (mission_parameters.json NOT FOUND)")
            return

        with open(MISSION_PARAMS, "r", encoding="utf-8") as f:
            params = json.load(f)

        target_repo = params.get("target_repo", "").split("/")[-1].replace(".git", "")
        repro_cmd = params.get("repro_cmd", "ls -R")
        fix_cmd = params.get("fix_cmd", "ls -R")
        entry_point = params.get("entry_point", "UNKNOWN")

        context = f"Target Repository: {target_repo}\nEntry Point: {entry_point}\nReproduction Cmd: {repro_cmd}\nVerification Cmd: {fix_cmd}\n\nPerform atomic iteration safely. Call FINISH when test passes."
        
        # Start Heartbeat Iteration
        self.execute_mission(context)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", help="Target repository")
    args = parser.parse_args()
    
    agent = CoderAgent()
    agent.spin_mission()

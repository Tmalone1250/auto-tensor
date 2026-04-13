import os
import json
import time
import uuid
from core.llm import LlmClient
from core.tools import v4_tool_registry, json_safe_parse

TASKS_DB = "logs/tasks.json"

class RepairPipeline:
    def __init__(self, repo_url: str, issue_description: str, task_id: str = None):
        self.task_id = task_id or str(uuid.uuid4())
        self.repo_url = repo_url
        self.issue_description = issue_description
        self.repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        self.repo_path = os.path.join("workspace", self.repo_name.lower())
        self.state = {
            "id": self.task_id,
            "repo_url": repo_url,
            "status": "INITIALIZING",
            "phase": "PRE-INIT",
            "logs": [],
            "retries": 0
        }
        self.llm = LlmClient()
        self.tools = v4_tool_registry
        self._sync_state()

    def _sync_state(self):
        os.makedirs("logs", exist_ok=True)
        if not os.path.exists(TASKS_DB):
            with open(TASKS_DB, "w") as f:
                json.dump({}, f)
        
        with open(TASKS_DB, "r") as f:
            try:
                db = json.load(f)
            except:
                db = {}
        
        db[self.task_id] = self.state
        with open(TASKS_DB, "w") as f:
            json.dump(db, f, indent=2)

    def log(self, phase: str, msg: str):
        self.state["phase"] = phase
        self.state["logs"].append({
            "timestamp": time.strftime("%H:%M:%S"),
            "phase": phase,
            "message": msg
        })
        self._sync_state()

    def run(self):
        self.state["status"] = "RUNNING"
        self._sync_state()

        try:
            # Phase 1: Structural Ingestion
            self.log("INGESTING", "Mapping repository structural tree...")
            repo_map_res = self.tools["tool_map_repo"](repo_path=self.repo_path)
            
            self.log("INGESTING", "Extracting framework entry point hashes...")
            entry_points_res = self.tools["tool_grep_entry"](repo_path=self.repo_path)
            
            context = f"REPO MAP:\n{repo_map_res.get('output', '')}\n\nENTRY POINTS:\n{entry_points_res.get('output', '')}"
            self.log("INGESTING", "Structural bounds constructed successfully.")

            # Phase 2: Root Cause Analysis
            self.log("ANALYZING", "Requesting Unified Json diff plan from Governor...")
            sys_prompt = "You are a strict structural patching mechanism. Return exclusively valid JSON dict. Keys required: 'target_file' (string path), 'search_block' (string, exact verbatim to replace), 'replace_block' (string, the fix), 'reasoning' (string). The problem is likely a missing script tag. Generate the atomic edit."
            
            prompt = f"Issue Detected: {self.issue_description}\nContext:\n{context}\n\nProvide the strict JSON execution plan."
            
            llm_response = self.llm.generate(prompt, system_override=sys_prompt)
            plan = json_safe_parse(llm_response)
            
            if "error" in plan:
                raise Exception(f"JSON Planning Parse Error: {plan['error']}")

            self.log("ANALYZING", f"Plan Synthesized. Target designated: {plan.get('target_file')}")
            
            # Phase 3 & 4: The Verified Execution Loop
            max_retries = 3
            success = False
            
            while self.state["retries"] < max_retries and not success:
                self.log("EXECUTING", f"Dropping atomic chunk patch to {plan.get('target_file')}...")
                
                patch_res = self.tools["apply_patch"](
                    path=os.path.join(self.repo_path, plan.get("target_file", "").replace("./", "")), 
                    search_block=plan.get("search_block", ""), 
                    replace_block=plan.get("replace_block", "")
                )
                
                if patch_res.get("status") == "FAIL":
                    self.log("EXECUTING", f"Patch rejection: {patch_res.get('output')}")
                    # To prevent infinite crashing on bad JSON diff
                    raise Exception(f"Execution failed on file diff match: {patch_res.get('output')}")

                self.log("VERIFYING", "Running explicit verification tests...")
                
                # Check for tag existence
                v_res = self.tools["verify_fix"](
                    repo_path=self.repo_path,
                    command="grep '<script type=\"module\" src=\"/src/main.tsx\"></script>' index.html"
                )
                
                if v_res.get("status") == "SUCCESS":
                    self.log("VERIFYING", "Verification hooks cleared successfully!")
                    success = True
                else:
                    self.state["retries"] += 1
                    self.log("VERIFYING", f"Verification mismatch. Retry {self.state['retries']}/{max_retries}")

            if success:
                self.state["status"] = "COMPLETED"
                self.log("COMPLETED", "Repair Pipeline terminated successfully.")
            else:
                self.state["status"] = "FAILED"
                self.log("FAILED", "Pipeline halted due to maximum threshold violations.")
                
        except Exception as e:
            self.state["status"] = "FAILED"
            self.log("FAILED", str(e))
                
        return self.state

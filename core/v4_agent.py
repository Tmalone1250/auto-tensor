import os
import json
import time
from core.llm import LlmClient
from core.tools import v4_tool_registry, json_safe_parse

STATE_LOG = "logs/mission_state.json"

class V4Agent:
    def __init__(self, mission_id: str, identity_file: str = "instructions_coder.md"):
        self.mission_id = mission_id
        self.llm = LlmClient()
        self.tools = v4_tool_registry
        
        # Grounding: Loading exact MD rules only
        identity_path = os.path.join("agents", "instructions", identity_file)
        self.system_prompt = self.llm.system_prompt
        if os.path.exists(identity_path):
            with open(identity_path, "r", encoding="utf-8") as f:
                self.system_prompt += f"\n\nMISSION CONSTRAINTS:\n{f.read()}"

        os.makedirs("logs", exist_ok=True)
        self.state = {
            "mission_id": self.mission_id,
            "status": "INITIALIZING",
            "turns": 0,
            "history": []
        }
        self.flush_state()

    def flush_state(self):
        with open(STATE_LOG, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def log_turn(self, call_type: str, data: dict):
        self.state["turns"] += 1
        self.state["history"].append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": call_type,
            "data": data
        })
        self.flush_state()

    def run_mission_loop(self, initial_context: str):
        self.state["status"] = "THINKING"
        self.flush_state()
        
        context_log = initial_context
        mission_complete = False

        while not mission_complete:
            prompt = (f"STATE: DECISION_REQUIRED\n"
                      f"TASK CONTEXT:\n{context_log}\n\n"
                      "Analyze context and provide action as a valid JSON object. {'action': 'FINISH'|'TOOL', 'tool': 'tool_name', 'args': {<kwargs>}}. No other text allowed.")

            response = self.llm.generate(prompt, system_override=self.system_prompt)
            parsed = json_safe_parse(response)

            if "error" in parsed:
                context_log += f"\n\n[SYSTEM] JSON Parse Error: {parsed['error']}. Ensure strictly valid JSON."
                self.log_turn("ERROR", {"msg": "JSON parse error", "raw": str(response)})
                continue

            action = parsed.get("action", "")

            if action == "FINISH":
                mission_complete = True
                self.state["status"] = "COMPLETED"
                self.log_turn("FINISH", parsed)
                break

            elif action == "TOOL":
                tool_name = parsed.get("tool")
                args = parsed.get("args", {})
                
                self.log_turn("TOOL_CALL", {"tool": tool_name, "args": args})
                
                if tool_name not in self.tools:
                    res = {"status": "FAIL", "output": f"Unknown tool: {tool_name}", "next_state": "DECISION_REQUIRED"}
                else:
                    print(f"[{self.mission_id}] Invoking {tool_name}...")
                    tool_func = self.tools[tool_name]
                    try:
                        res = tool_func(**args)
                    except Exception as e:
                        res = {"status": "FAIL", "output": str(e), "next_state": "DECISION_REQUIRED"}
                
                self.log_turn("TOOL_RESULT", res)
                context_log += f"\n\n--- TOOL RESULT: {tool_name} ---\n{str(res.get('output'))[:3000]}"
            else:
                context_log += f"\n\n[SYSTEM] Invalid action type. Use FINISH or TOOL."
                self.log_turn("ERROR", {"msg": "Invalid Action", "raw": str(action)})
                
        return self.state

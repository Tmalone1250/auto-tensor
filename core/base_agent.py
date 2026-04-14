import json
from core.llm import LlmClient
from core.persona import get_system_prompt

class BaseAgent:
    def __init__(self, agent_name: str, config: dict = None):
        self.agent_name = agent_name
        self.config = config or {}
        self.llm = LlmClient()
        self.system_prompt = self._load_identity()
        self.mission_complete = False
        self._load_tools()
        
    def _load_identity(self) -> str:
        return get_system_prompt(self.agent_name)

    def update_instructions(self, custom_instr: str):
        self.system_prompt = get_system_prompt(self.agent_name, custom_instr)

    def _load_tools(self):
        from core.tools.common import execute_mission_step, tool_safe_exec, reflect_and_memorize, json_safe_parse
        from core.tools.scout_ops import tool_get_repo_map, tool_grep_codebase, tool_identify_cli, tool_summarize_file, tool_rank_issues, tool_fetch_issues
        from core.tools.coder_ops import surgical_read, surgical_write, tool_read_file_range, tool_atomic_replace

        self.tools = {
            "execute_mission_step": execute_mission_step,
            "tool_safe_exec": tool_safe_exec,
            "reflect_and_memorize": reflect_and_memorize,
            "tool_get_repo_map": tool_get_repo_map,
            "tool_grep_codebase": tool_grep_codebase,
            "tool_identify_cli": tool_identify_cli,
            "tool_summarize_file": tool_summarize_file,
            "tool_rank_issues": tool_rank_issues,
            "tool_fetch_issues": tool_fetch_issues,
            "surgical_read": surgical_read,
            "surgical_write": surgical_write,
            "tool_read_file_range": tool_read_file_range,
            "tool_atomic_replace": tool_atomic_replace
        }

    def invoke_tool(self, tool_name: str, **kwargs):
        """Standardized tool invocation execution limit."""
        if tool_name not in self.tools:
            return f"CRITICAL_FAILURE: Unknown tool '{tool_name}'"
        
        tool_func = self.tools[tool_name]
        print(f"[{self.agent_name.capitalize()}] Invoking {tool_name}...")
        try:
            return tool_func(**kwargs)
        except Exception as e:
            return f"CRITICAL_FAILURE in {tool_name}: {str(e)}"

    def route(self, task_context: str, state: str = "DECISION_REQUIRED") -> str:
        if state not in ["DECISION_REQUIRED", "CRITICAL_FAILURE"]:
            print(f"[{self.agent_name.capitalize()}] Skipping LLM route: State is {state}")
            return "SUCCESS"
            
        print(f"[{self.agent_name.capitalize()}] Routing context due to state: {state}")
        prompt = (f"STATE: {state}\n"
                  f"TASK CONTEXT:\n{task_context}\n\n"
                  "Analyze and provide your next action as a JSON object with 'Reasoning' (string detailing logic), 'action' (FINISH or TOOL), 'tool' (name of tool if action is TOOL), and 'args' (a dict of kwargs). Do not include any other text.")
        return self.llm.generate(prompt, system_override=self.system_prompt)

    def execute_mission(self, initial_context: str):
        from core.tools.common import json_safe_parse
        self.mission_complete = False
        context_log = initial_context
        
        while not self.mission_complete:
            response = self.route(context_log, state="DECISION_REQUIRED")
            parsed = json_safe_parse(response)
            
            if "error" in parsed:
                 context_log += f"\n\nJSON Parsing Failure. Expected pure JSON Object: {parsed['error']}"
                 continue
                 
            if "Reasoning" not in parsed and "reasoning" not in parsed:
                 context_log += f"\n\nJSON Integrity Failure. Missing explicitly required 'Reasoning' dict key. Fix state block."
                 continue
                 
            reasoning = parsed.get("Reasoning", parsed.get("reasoning", ""))
            print(f"[{self.agent_name.capitalize()} Reasoning]: {reasoning}")
                 
            action = parsed.get("action", "")
            
            if action == "FINISH":
                self.mission_complete = True
                print(f"[{self.agent_name.capitalize()}] Heartbeat: Mission successfully finalized.")
                
                # Reflection Trigger
                try:
                    args = parsed.get("args", {})
                    target_repo = args.get("target_repo", "UNKNOWN")
                    entry = args.get("entry_point", "cli.py")
                    success_cmd = args.get("fix_cmd", "python3 " + entry)
                    
                    self.invoke_tool("reflect_and_memorize", agent=self.agent_name, target_repo=target_repo, entry_point=entry, success_cmd=success_cmd)
                except Exception as e:
                    print(f"[{self.agent_name.capitalize()}] Reflection trace failed: {str(e)}")
                    
                return parsed
            elif action == "TOOL":
                tool_name = parsed.get("tool")
                args = parsed.get("args", {})
                tool_result = self.invoke_tool(tool_name, **args)
                context_log += f"\n\n--- TOOL RESULT: {tool_name} ---\n{str(tool_result)[:2000]}"
            else:
                context_log += f"\n\nInvalid action format. Expected 'FINISH' or 'TOOL'."
                
        return None

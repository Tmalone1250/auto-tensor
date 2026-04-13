import json
from core.llm import LlmClient
from core.persona import get_system_prompt

class BaseAgent:
    def __init__(self, agent_name: str, config: dict = None):
        self.agent_name = agent_name
        self.config = config or {}
        self.llm = LlmClient()
        self.system_prompt = self._load_identity()
        
    def _load_identity(self) -> str:
        return get_system_prompt(self.agent_name)

    def update_instructions(self, custom_instr: str):
        self.system_prompt = get_system_prompt(self.agent_name, custom_instr)

    def invoke_tool(self, tool_func, *args, **kwargs):
        """Standardized tool invocation execution limit."""
        print(f"[{self.agent_name.capitalize()}] Invoking {tool_func.__name__}...")
        try:
            return tool_func(*args, **kwargs)
        except Exception as e:
            return f"CRITICAL_FAILURE in {tool_func.__name__}: {str(e)}"

    def route(self, task_context: str, state: str = "DECISION_REQUIRED") -> str:
        """Only calls LLM if state hits specific failure or decision flags."""
        if state not in ["DECISION_REQUIRED", "CRITICAL_FAILURE"]:
            print(f"[{self.agent_name.capitalize()}] Skipping LLM route: State is {state}")
            return "SUCCESS" # Bypass if deterministic path holds
            
        print(f"[{self.agent_name.capitalize()}] Routing context due to state: {state}")
        prompt = f"STATE: {state}\nTASK CONTEXT:\n{task_context}\n\nAnalyze and provide tool instructions or final report."
        return self.llm.generate(prompt, system_override=self.system_prompt)

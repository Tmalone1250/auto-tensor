import os
import subprocess
import json

def execute_mission_step(path: str, command: str) -> str:
    """Encapsulates execution securely mapping to the workspace."""
    workspace_path = os.path.join("workspace", path)
    if not os.path.exists(workspace_path):
         return f"Error: Path {workspace_path} does not exist"
    
    try:
         result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=workspace_path, timeout=600)
         return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
         return "Command Execution Timeout"
    except Exception as e:
         return str(e)

def json_safe_parse(raw_str: str) -> dict:
    """Python native JSON parsing to handle LLM artifacts safely."""
    clean = raw_str.strip().strip("```json").strip("```").strip()
    try:
        return json.loads(clean)
    except Exception as e:
        return {"error": f"JSON parse failure: {str(e)}"}

def tool_safe_exec(cmd: str, timeout: int = 60) -> str:
    forbidden = ["sudo", "rm -rf /", "wsl", "stty"]
    for f in forbidden:
        if f in cmd:
            return f"Security Error: Command contains forbidden prefix '{f}'"
            
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return f"Execution timeout after {timeout} seconds."
    except Exception as e:
        return f"Execution Error: {str(e)}"

def reflect_and_memorize(agent_name: str, repo: str, entry_point: str, strategy_cmd: str) -> str:
    """Writes the exact Schema-First Markdown sequence to the skills log."""
    path = f"agents/skills/skills_{agent_name}.md"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    entry = f"- [{repo}] | [{entry_point}] | [{strategy_cmd}]\n"
    
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if entry.strip() in content:
                return "Memory exists natively."
        
        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)
        return "Reflection successful."
    except Exception as e:
        return f"Reflection Error: {str(e)}"

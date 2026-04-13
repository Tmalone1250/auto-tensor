import os
import subprocess
import json
from functools import wraps

def v4_tool(func):
    """V4 standardized response enforced wrapper to guarantee unified API outputs."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            res = func(*args, **kwargs)
            if isinstance(res, str) and ("Error" in res or "Exception" in res):
                return {"status": "FAIL", "output": res, "next_state": "DECISION_REQUIRED"}
            return {"status": "SUCCESS", "output": res, "next_state": "DECISION_REQUIRED"}
        except Exception as e:
            return {"status": "FAIL", "output": str(e), "next_state": "DECISION_REQUIRED"}
    return wrapper

@v4_tool
def execute_mission_step(path: str, command: str) -> str:
    workspace_path = os.path.join("workspace", path)
    if not os.path.exists(workspace_path):
         return f"Error: Path {workspace_path} does not exist."
    try:
         result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=workspace_path, timeout=600)
         if result.returncode != 0:
             return f"Error Execution [{result.returncode}]:\n{result.stderr}"
         return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
         return "Error Execution Timeout."
    except Exception as e:
         return f"Error: {str(e)}"

@v4_tool
def surgical_read(file_path: str) -> str:
    if not os.path.exists(file_path):
        return f"Error: File {file_path} not found."
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return "".join(f"{i+1}: {line}" for i, line in enumerate(lines))

@v4_tool
def surgical_write(file_path: str, new_content: str) -> str:
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    if file_path.endswith('.py'):
        check_cmd = f"python3 -m py_compile {file_path}"
        result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            return f"Error Syntax during write verification:\n{result.stderr}"
    return "Write successful and syntax verified."

@v4_tool
def tool_read_file_range(path: str, start_line: int, end_line: int) -> str:
    if not os.path.exists(path):
        return f"Error: File {path} not found."
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    start_idx = max(0, start_line - 1)
    end_idx = min(len(lines), end_line)
    return "".join(f"{i+start_line}: {line}" for i, line in enumerate(lines[start_idx:end_idx]))

@v4_tool
def tool_atomic_replace(path: str, search_block: str, replace_block: str) -> str:
    if not os.path.exists(path):
        return f"Error: File {path} not found."
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    occurrences = content.count(search_block)
    if occurrences == 0:
        return "Error: search_block not found in file. Ensure exact matching including whitespace."
    elif occurrences > 1:
        return f"Error: search_block found {occurrences} times. Block must be completely unique."
        
    new_content = content.replace(search_block, replace_block)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    if path.endswith('.py'):
        check = f"python3 -m py_compile {path}"
        if subprocess.run(check, shell=True, capture_output=True).returncode != 0:
            return "Error: Syntax check failed on replace step."
    return "Atomic replace successful."

@v4_tool
def tool_get_repo_map(max_depth: int = 3, repo_path: str = ".") -> str:
    if not os.path.exists(repo_path):
        return f"Error: Path {repo_path} does not exist."
    cmd = ["find", repo_path, "-maxdepth", str(max_depth), "-not", "-path", "*/.git/*", "-not", "-path", "*/__pycache__/*", "-not", "-path", "*/node_modules/*"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

@v4_tool
def tool_grep_codebase(regex_pattern: str, repo_path: str = ".") -> str:
    cmd = ["grep", "-rnE", regex_pattern, repo_path, "--exclude-dir=.git", "--exclude-dir=__pycache__", "--exclude-dir=node_modules"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout[:5000]

@v4_tool
def tool_grep_entry(repo_path: str = ".") -> str:
    if not os.path.exists(repo_path):
        return f"Error: Path {repo_path} does not exist."
    cmd = ["find", repo_path, "-name", "index.html", "-o", "-name", "main.tsx", "-o", "-name", "App.tsx"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

@v4_tool
def verify_fix(repo_path: str, command: str) -> str:
    if not os.path.exists(repo_path):
        return f"Error: Path {repo_path} does not exist."
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=repo_path, timeout=120)
        if result.returncode != 0:
            return f"Error Verify Failed [{result.returncode}]:\n{result.stderr}"
        return f"Verify Success:\n{result.stdout}"
    except Exception as e:
        return f"Error: {str(e)}"

def json_safe_parse(raw_str: str) -> dict:
    """Non-V4 helper wrapper for native core JSON parsing."""
    clean = raw_str.strip().strip("```json").strip("```").strip()
    try:
        return json.loads(clean)
    except Exception as e:
        return {"error": f"JSON parse failure: {str(e)}"}

v4_tool_registry = {
    "execute_mission_step": execute_mission_step,
    "surgical_read": surgical_read,
    "surgical_write": surgical_write,
    "tool_read_file_range": tool_read_file_range,
    "tool_atomic_replace": tool_atomic_replace,
    "apply_patch": tool_atomic_replace,
    "tool_get_repo_map": tool_get_repo_map,
    "tool_map_repo": tool_get_repo_map,
    "tool_grep_codebase": tool_grep_codebase,
    "tool_grep_entry": tool_grep_entry,
    "verify_fix": verify_fix
}

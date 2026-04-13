"""
core/tools.py — Coder Tooling Layer
The Terminate-Hallucination Patch
"""
import os
import json
import subprocess

MISSION_PARAMS = "logs/mission_parameters.json"

def get_mission_context():
    if not os.path.exists(MISSION_PARAMS):
        raise FileNotFoundError("mission_parameters.json not found.")
    with open(MISSION_PARAMS, "r", encoding="utf-8") as f:
        return json.load(f)

def run_verified_cmd(subcommand: str) -> str:
    """
    Reads mission_parameters.json for the entry_point.
    Constructs the string and executes it.
    """
    try:
        params = get_mission_context()
        entry_point = params.get("entry_point")
        if not entry_point:
            return "Error: entry_point not provided in mission_parameters."
            
        repo_raw = params.get("target_repo", "")
        repo_folder = repo_raw.split("/")[-1].replace(".git", "")
        workspace_path = os.path.join("workspace", repo_folder)
            
        cmd = f'bash -c "export COLUMNS=40; uv run --active python3 {entry_point} {subcommand}"'
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=workspace_path)
        return result.stdout + result.stderr
    except Exception as e:
        return f"Execution Error: {str(e)}"

def surgical_read(file_path: str) -> str:
    """Returns file content with line numbers for precision editing."""
    if not os.path.exists(file_path):
        return f"Error: File {file_path} not found."
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        return "".join(f"{i+1}: {line}" for i, line in enumerate(lines))
    except Exception as e:
        return f"Read Error: {str(e)}"

def surgical_write(file_path: str, new_content: str) -> str:
    """Writes content and performs a python3 -m compileall check to ensure no syntax errors were introduced."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        # Compileall check to verify python syntax
        if file_path.endswith('.py'):
            check_cmd = f"python3 -m py_compile {file_path}"
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                return f"Syntax Error during verification:\n{result.stderr}"
            
        return "Write successful and syntax verified."
    except Exception as e:
        return f"Write Error: {str(e)}"

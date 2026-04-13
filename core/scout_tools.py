import os
import subprocess
import json

def tool_get_repo_map(max_depth: int = 3, repo_path: str = ".") -> str:
    """Returns a directory tree ignoring .git, __pycache__, and node_modules."""
    cmd = ["find", repo_path, "-maxdepth", str(max_depth), "-not", "-path", "*/.git/*", "-not", "-path", "*/__pycache__/*", "-not", "-path", "*/node_modules/*"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"Error mapping repo: {e}"

def tool_grep_codebase(regex_pattern: str, repo_path: str = ".") -> str:
    """Executes a fast search across the workspace for specific logic (e.g., 'database', 'orphan', 'cleanup')."""
    cmd = ["grep", "-rnE", regex_pattern, repo_path, "--exclude-dir=.git", "--exclude-dir=__pycache__", "--exclude-dir=node_modules"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout[:5000] # Cap output to prevent blowups
    except Exception as e:
        return f"Error searching codebase: {e}"

def tool_identify_cli(repo_path: str = ".") -> str:
    """Scans the codebase specifically for the most likely execution entry points."""
    cmd = ["grep", "-rlE", "import (click|argparse|typer)|from (click|argparse|typer)", repo_path, "--exclude-dir=.git", "--exclude-dir=__pycache__", "--exclude-dir=node_modules"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        files = [f for f in result.stdout.strip().split('\n') if f]
        
        scored = []
        for file in files:
            score = 1
            if "main" in file: score += 5
            if "cli" in file: score += 5
            if "run" in file: score += 3
            if "/" not in file.replace(repo_path, "").strip("/"): score += 2 # Root level
            scored.append({"file": file, "confidence": score})
            
        scored.sort(key=lambda x: x["confidence"], reverse=True)
        return json.dumps(scored, indent=2)
    except Exception as e:
        return f"Error identifying CLI: {e}"

def tool_summarize_file(file_path: str) -> str:
    """Instead of reading the whole file, returns only the Class and Function names."""
    if not os.path.exists(file_path):
        return f"Error: File {file_path} not found"
        
    cmd = ["grep", "-nE", "^class |^ *def |^const |^function ", file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"Error summarizing file: {e}"

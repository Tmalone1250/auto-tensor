import os
import subprocess

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
    """Writes content and performs a python3 -m compileall check to ensure no syntax errors."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        if file_path.endswith('.py'):
            check_cmd = f"python3 -m py_compile {file_path}"
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                return f"Syntax Error during verification:\n{result.stderr}"
        return "Write successful and syntax verified."
    except Exception as e:
        return f"Write Error: {str(e)}"

def tool_read_file_range(path: str, start_line: int, end_line: int) -> str:
    if not os.path.exists(path):
        return f"Error: File {path} not found."
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        ranged_lines = lines[start_idx:end_idx]
        return "".join(f"{i+start_line}: {line}" for i, line in enumerate(ranged_lines))
    except Exception as e:
        return f"Read Error: {str(e)}"

def tool_atomic_replace(path: str, search_block: str, replace_block: str) -> str:
    if not os.path.exists(path):
        return f"Error: File {path} not found."
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        occurrences = content.count(search_block)
        if occurrences == 0:
            return "Error: search_block not found in file."
        elif occurrences > 1:
            return f"Error: search_block found {occurrences} times. Must be unique."
            
        new_content = content.replace(search_block, replace_block)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        if path.endswith('.py'):
            check_cmd = f"python3 -m py_compile {path}"
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                return f"Syntax Error introduced.\n{result.stderr}"
                
        return "Atomic replace successful."
    except Exception as e:
        return f"Write Error: {str(e)}"

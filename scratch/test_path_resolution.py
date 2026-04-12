import os
import sys

def get_venv_python():
    if sys.platform == "win32":
        venv_python = os.path.join(".venv", "Scripts", "python.exe")
    else:
        venv_python = os.path.join(".venv", "bin", "python")

    # Fallback logic for mismatched environments (e.g. Linux venv on Windows)
    if not os.path.exists(venv_python):
        alt_python = os.path.join(".venv", "bin", "python") if sys.platform == "win32" else os.path.join(".venv", "Scripts", "python.exe")
        if os.path.exists(alt_python):
            return alt_python
        else:
            return sys.executable
    return venv_python

print(f"Platform: {sys.platform}")
print(f"Resolved Python: {get_venv_python()}")
print(f"File exists: {os.path.exists(get_venv_python())}")

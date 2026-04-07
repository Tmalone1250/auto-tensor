"""
check_deps.py — Auto-Tensor Environment Audit v2
Run via: ./.venv/bin/python check_deps.py
Verifies all system tools AND confirms execution inside the .venv.
"""
import subprocess
import sys
import os

# ─── venv Enforcement ────────────────────────────────────────────────────────
VENV_PYTHON = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".venv", "bin", "python")

def check_venv():
    inside = sys.prefix != sys.base_prefix
    marker = "[OK]  " if inside else "[WARN]"
    print(f"{marker} Virtual Environment: {'ACTIVE (' + sys.prefix + ')' if inside else 'NOT ACTIVE — run via .venv/bin/python'}")
    return inside

# ─── python-dotenv: Load .env ─────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[OK]  python-dotenv: .env loaded")
except ImportError:
    print("[FAIL] python-dotenv not installed in this environment")

# ─── Python Package Checks ────────────────────────────────────────────────────
def check_package(name: str, import_name: str = None):
    import_name = import_name or name
    try:
        mod = __import__(import_name)
        version = getattr(mod, "__version__", "?")
        print(f"[OK]  {name}: {version}")
        return True
    except ImportError:
        print(f"[FAIL] {name} is not installed in this environment")
        return False

# ─── System Tool Checks (via WSL) ─────────────────────────────────────────────
def check_tool(command: str, name: str):
    try:
        result = subprocess.run(
            ["wsl", "bash", "-c", f"source ~/.bashrc 2>/dev/null; {command}"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            version = result.stdout.strip().split("\n")[0]
            print(f"[OK]  {name}: {version}")
            return True
        else:
            print(f"[FAIL] {name}: {result.stderr.strip()[:80]}")
            return False
    except FileNotFoundError:
        print(f"[MISSING] {name}")
        return False

# ─── Main Audit ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  Auto-Tensor Environment Audit v2")
    print("=" * 50)

    print("\n[-- Python Environment --]")
    venv_ok = check_venv()
    print(f"     Python binary : {sys.executable}")
    print(f"     Python version: {sys.version.split()[0]}")

    print("\n[-- Python Packages --]")
    req_ok  = check_package("requests")
    yaml_ok = check_package("PyYAML", "yaml")
    env_ok  = check_package("python-dotenv", "dotenv")

    print("\n[-- System Tools (WSL) --]")
    go_ok     = check_tool("go version", "Go")
    just_ok   = check_tool("just --version", "Just")
    rust_ok   = check_tool("rustc --version", "Rust")
    forge_ok  = check_tool("forge --version", "Foundry")
    docker_ok = check_tool("docker.exe --version", "Docker")

    print("\n[-- Summary --]")
    all_py_ok = venv_ok and req_ok and yaml_ok and env_ok
    print(f"  Python stack : {'PASS' if all_py_ok else 'WARN — missing packages or not in venv'}")
    print(f"  Docker       : {'PASS' if docker_ok else 'BLOCKED — cannon builds will fail'}")
    print(f"  Rust toolchain: {'PASS' if rust_ok else 'MISSING'}")
    print("=" * 50 + "\n")

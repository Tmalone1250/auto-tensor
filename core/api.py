import os
from dotenv import load_dotenv
load_dotenv()
import shutil
import time
import sys
import subprocess
import json
import traceback
import uuid
import logging
import requests
import contextlib
import asyncio
from datetime import datetime
from typing import Optional, List, Dict

print("[SYSTEM]: All required libraries (requests, fastapi, pydantic) verified.")

# Ensure root is in sys.path (Absolute Priority)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Body, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
try:
    from core.terminal import PtyManager
    from core.terminal_manager import terminal_manager
except ImportError as e:
    print(f"[SYSTEM]: Terminal Native PTY constrained. {e}")
    PtyManager = None
    terminal_manager = None

GITHUB_KEY = os.getenv("GITHUB_KEY")
print(f"DEBUG: GitHub Token Loaded. Starts with: {GITHUB_KEY[:4] if GITHUB_KEY else 'NONE'}")

# Terminal shell secret — validated on WebSocket handshake
TERMINAL_SECRET = os.getenv("TERMINAL_SECRET", "")

# --- Global State Manager ---
SYSTEM_STATE = {
    "active_agent": "None",
    "is_running": False,
    "current_repo": "None",
    "last_run": None,
    "provisioned_repos": [], # Local folders in workspace/
    "verified_repos": []     # Repos that have passed grounding
}

# --- State Management ---
REGISTRY_PATH = "core/registry.json"
APPROVALS_PATH = "logs/approvals.json"

from core.health_check import check_rate_limit
from core.skill_writer import record_mission_success
from agents.memory_helper import ReflectionEngine

app = FastAPI(title="Auto-Tensor Command Bridge")

@app.on_event("startup")
async def startup_event():
    os.makedirs("workspace", exist_ok=True)
    await terminal_manager.start_gc()

# --- Models ---
class AgentRequest(BaseModel):
    agent_name: str

class IgnoreRequest(BaseModel):
    issue_id: int
    target: Optional[str] = None

class RepoRequest(BaseModel):
    url: str

class ApprovalAction(BaseModel):
    id: str
    action: str # "commit", "draft", "publish"

class ProvisionRequest(BaseModel):
    target_repo: Optional[str] = None # Full HTTPS URL
    url: Optional[str] = None # Fallback key

class VerifyRequest(BaseModel):
    repo_path: str # The folder name in workspace/

def load_json(path: str, default: dict) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# --- V4 Maggie Sniper Orchestrator ---
def run_maggie_sync(url: str):
    from agents.maggie import MaggieAgent
    try:
        agent = MaggieAgent()
        agent.scan(target_repo=url)
    except Exception as e:
        import traceback
        traceback.print_exc()

class ProcessManagerStub:
    self_start_time = time.time()
    def __init__(self):
        self.start_time = time.time()

pm = ProcessManagerStub()

# --- CORS ---
# --- CORS Hardening for Hybrid Deployment ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",          # Local Development
        "https://auto-tensor.vercel.app",   # Future Production Vercel (Primary)
        "https://*.vercel.app"              # Vercel Preview Deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status")
def get_status():
    """Returns GitHub Quota, Uptime, and Process Status with Disk-Aware Provisioning."""
    rate_limit = check_rate_limit()
    uptime_seconds = int(time.time() - pm.start_time)
    
    # Dynamic Disk Scanning: Look at what's actually on the VPS
    workspace_path = "workspace"
    disk_repos = []
    if os.path.exists(workspace_path):
        disk_repos = [
            f for f in os.listdir(workspace_path) 
            if os.path.isdir(os.path.join(workspace_path, f))
        ]
    
    global SYSTEM_STATE
    SYSTEM_STATE["provisioned_repos"] = list(set(disk_repos))
    
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    active_agent = SYSTEM_STATE["active_agent"]
    is_running = SYSTEM_STATE["is_running"]
    current_task = f"Executing {active_agent} mission..." if is_running else "Idle"

    # Needs Verification check
    needs_verification = False
    provisioned = SYSTEM_STATE["provisioned_repos"]
    verified = SYSTEM_STATE["verified_repos"]
    for repo in provisioned:
        if repo not in verified:
            needs_verification = True
            break

    return {
        "github_status": rate_limit,
        "miner_uptime": uptime_str,
        "active_agent": active_agent,
        "is_running": is_running,
        "current_task": current_task,
        "timestamp": datetime.now().isoformat(),
        "provisioned_repos": provisioned,
        "verified_repos": verified,
        "needs_verification": needs_verification
    }

@app.get("/scout/report")
def get_scout_report():
    path = "logs/scout_report.json"
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"status": "LOADING"}
    return {"status": "NO_REPORT_FOUND"}

# --- Provisioning Logic ---
def get_provision_folder(url: str) -> str:
    return url.rstrip("/").split("/")[-1].replace(".git", "")

async def poll_fork_status(fork_url: str, headers: dict) -> bool:
    """Retries 3 times to ensure the fork is actually provisioned on GitHub."""
    parts = fork_url.rstrip("/").split("/")
    owner, repo = parts[-2], parts[-1]
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    
    for i in range(3):
        try:
            res = requests.get(api_url, headers=headers, timeout=10)
            if res.status_code == 200:
                return True
        except:
            pass
        await asyncio.sleep(10) # 10s wait between retries
    return False

async def run_provision_logic(url: str, folder: str, workspace_path: str):
    """
    Background worker for infrastructure setup.
    Hardened with localized logging and permission guards.
    """
    log_path = os.path.join("logs", "workflow.log")
    os.makedirs("logs", exist_ok=True)
    
    # Priority 1: Logging init (using global logging)
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    
    token = os.getenv("GITHUB_KEY")
    
    try:
        # 1. Robust URL Parsing (Redundant but safe for background context)
        parts = url.rstrip("/").split("/")
        owner, repo_name = parts[-2], parts[-1].replace(".git", "")
        
        # 2. Disk Safety sandbox
        if os.path.exists(workspace_path):
            shutil.rmtree(workspace_path)
        
        # 3. Token Check
        if not token:
            raise Exception("GITHUB_KEY missing in background context.")

        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}

        # 4. Fork
        fork_api_url = f"https://api.github.com/repos/{owner}/{repo_name}/forks"
        res = requests.post(fork_api_url, headers=headers, timeout=30)
        
        # Priority: Specific Permission Denied Logging
        if res.status_code in [401, 403]:
             logging.error(f"[PERMISSION DENIED] GitHub API failed for {url}. Status: {res.status_code}")
             raise Exception(f"PERMISSION DENIED: Check GITHUB_KEY. ({res.status_code})")
             
        if res.status_code not in [201, 202]:
            raise Exception(f"Fork failed: {res.status_code} - {res.text}")

        fork_data = res.json()
        fork_url = fork_data.get("html_url")
        fork_owner = fork_data.get("owner", {}).get("login")
        author_assoc = fork_data.get("source", {}).get("owner", {}).get("type", "User") # Approximate for now

        # 5. Polling
        logging.info(f"Forking repository... Polling for readiness at {fork_url}")
        if not await poll_fork_status(fork_url, headers):
            raise Exception("GitHub Fork provision timed out.")

        # 6. Branch
        repo_info = requests.get(f"https://api.github.com/repos/{fork_owner}/{repo_name}", headers=headers).json()
        default_branch = repo_info.get("default_branch", "main")
        ref_url = f"https://api.github.com/repos/{fork_owner}/{repo_name}/git/refs/heads/{default_branch}"
        base_sha = requests.get(ref_url, headers=headers).json().get("object", {}).get("sha")
        
        branch_name = "auto-tensor-dev"
        create_br_url = f"https://api.github.com/repos/{fork_owner}/{repo_name}/git/refs"
        requests.post(create_br_url, headers=headers, json={"ref": f"refs/heads/{branch_name}", "sha": base_sha})

        # 7. Clone
        auth_clone_url = fork_url.replace("https://github.com/", f"https://{token}@github.com/")
        os.makedirs("workspace", exist_ok=True)
        subprocess.run(["git", "clone", "-b", branch_name, auth_clone_url, workspace_path], check=True, capture_output=True)

        # 8. State Sync
        global SYSTEM_STATE
        if folder not in SYSTEM_STATE["provisioned_repos"]:
            SYSTEM_STATE["provisioned_repos"].append(folder)
        
        registry = load_json(REGISTRY_PATH, {"repos": []})
        for r in registry["repos"]:
            if r["html_url"].lower() == url.lower():
                r["provisioned"] = True
                r["provision_folder"] = folder
                r["provisioned_at"] = datetime.now().isoformat()
        save_json(REGISTRY_PATH, registry)

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] [PROVISION] Success: {folder}\n")

    except Exception as e:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] [CRITICAL] Background Provisioning Failed for {url}:\n")
            f.write(f"Detail: {str(e)}\n")
            f.write(traceback.format_exc())
            f.write("-" * 40 + "\n")

@app.post("/repo/provision")
async def provision_repository(request: ProvisionRequest, background_tasks: BackgroundTasks):
    """
    Refactored Agentic Hub Step: Delegates heavy lifting to background tasks.
    """
    url = (request.target_repo or request.url or "").strip()
    if not url or not url.startswith("https://github.com/"):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL format.")
    
    try:
        parts = url.rstrip("/").split("/")
        repo_name = parts[-1].replace(".git", "")
        folder = repo_name.lower()
        workspace_path = os.path.join("workspace", folder)
        
        # Verify safety
        normalized_path = os.path.abspath(workspace_path)
        workspace_root = os.path.abspath("workspace")
        if not normalized_path.startswith(workspace_root):
            raise HTTPException(status_code=403, detail="Forbidden target.")

        background_tasks.add_task(run_provision_logic, url, folder, workspace_path)
        
        return {"status": "started", "msg": "Provisioning initiated in background.", "folder": folder}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Repo Management ---
@app.get("/repos")
def get_repos():
    """Returns the list of managed repositories."""
    data = load_json(REGISTRY_PATH, {"repos": []})
    return data

@app.post("/repo/add")
def add_repo(request: RepoRequest):
    """Clones a repository and adds it to the registry."""
    url = request.url.strip()
    if not url.startswith("https://github.com/"):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")

    repo_name = url.split("/")[-1].replace(".git", "")
    org_name = url.split("/")[-2]
    full_id = f"{org_name}/{repo_name}"
    
    # Check if already exists
    registry = load_json(REGISTRY_PATH, {"repos": []})
    if any(r["full_name"] == full_id for r in registry["repos"]):
         return {"status": "exists", "id": full_id}

    # Perform Clone (in WSL)
    workspace_dir = os.path.join("workspace", repo_name)
    if not os.path.exists(workspace_dir):
        try:
            subprocess.run(["git", "clone", url, workspace_dir], check=True)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Clone failed: {str(e)}")

    # Update Registry
    new_repo = {
        "id": repo_name,
        "full_name": full_id,
        "html_url": url,
        "added_at": datetime.now().isoformat()
    }
    registry["repos"].append(new_repo)
    save_json(REGISTRY_PATH, registry)
    
    return {"status": "added", "repo": new_repo}

@app.post("/repo/scan")
def scan_repository(request: RepoRequest, background_tasks: BackgroundTasks):
    """Triggers the Maggie Intel sniper on a specific repository URL."""
    url = request.url.strip()
    if not url.startswith("https://github.com/"):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
        
    background_tasks.add_task(run_maggie_sync, url)
    return {"status": "started", "agent": "maggie", "target": url}

# --- Approvals Workflow ---
@app.get("/approvals")
def get_approvals():
    """Returns the list of pending approvals."""
    return load_json(APPROVALS_PATH, {"pending": []})

@app.post("/approvals/action")
def approval_action(action: ApprovalAction):
    """Executes a stage in the approval workflow."""
    if action.action == "publish":
        try:
            record_mission_success()
        except Exception as e:
            print(f"[API] Skill synthesis failed: {e}")
            
    return {"status": "success", "action": action.action, "id": action.id}

@app.get("/audit")
def get_audit():
    """Returns the contents of logs/simulation_audit.md."""
    audit_path = os.path.join("logs", "simulation_audit.md")
    if not os.path.exists(audit_path):
        return {"content": "No audit records found."}
    
    try:
        with open(audit_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        return {"error": str(e)}

@app.get("/logs")
def get_logs(agent: Optional[str] = None):
    """Returns the last 50 lines of the workflow log, optionally filtered by agent."""
    log_path = os.path.join("logs", "workflow.log")
    if agent == "scout":
        log_path = os.path.join("logs", "scout.log")
    
    if not os.path.exists(log_path):
        os.makedirs("logs", exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] WAR ROOM: Workflow logger initialized.\n")

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Filter by agent with multi-line support
        if agent:
            tag = f"[{agent.capitalize()}]"
            bored_tag = f"[Bored {agent.capitalize()}]"
            filtered = []
            capture_next = False
            
            for line in lines:
                is_tagged = tag in line or bored_tag in line or f"STARTING {agent.upper()}" in line
                
                if is_tagged:
                    filtered.append(line.strip())
                    # If the line looks like it starts a JSON block or an error, prepare to capture next
                    capture_next = line.strip().endswith("{") or "LLM Error" in line
                elif capture_next and not line.startswith("[") and not line.startswith("---"):
                    # This is a continuation line
                    filtered.append(f"  {line.strip()}")
                    if "}" in line or "]" in line:
                         capture_next = False # Close block
                else:
                    capture_next = False
            
            return {"logs": filtered[-50:]}
            
        return {"logs": [line.strip() for line in lines[-50:]]}
    except Exception as e:
        return {"error": str(e)}

@app.post("/scout/deprecated")
def legacy_scout_deprecated():
    return {"status": "DEPRECATED", "msg": "Use /mission/start for V4 execution payloads."}

@app.post("/logs/clear")
def clear_logs():
    """Wipes the active logs to prevent 'Sticky Logs' in the UI."""
    workflow_log = os.path.join("logs", "workflow.log")
    scout_log = os.path.join("logs", "scout.log")
    archive_dir = os.path.join("logs", "archive")
    
    try:
        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Handle Workflow Log (Archive)
        if os.path.exists(workflow_log):
            archive_path = os.path.join(archive_dir, f"workflow_{timestamp}.log")
            shutil.move(workflow_log, archive_path)
        
        # Start fresh workflow log
        with open(workflow_log, "w", encoding="utf-8") as f:
            f.write(f"--- [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] LOGS CLEARED BY OPERATOR ---\n")

        # Handle Scout Log (Truncate - Physical Wipe)
        # We use 'w' mode to truncate it to 0 bytes
        with open(scout_log, "w", encoding="utf-8") as f:
            pass 
            
        return {"status": "success", "msg": "Logs physically truncated and archived."}
    except Exception as e:
        # Return success if file doesn't exist, otherwise error
        if not os.path.exists(scout_log) and not os.path.exists(workflow_log):
             return {"status": "success", "msg": "Logs already clear."}
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scout/ignore")
def ignore_issue(req: IgnoreRequest = Body(...)):
    """Removes an issue from the scout report permanently."""
    report_path = os.path.join("logs", "scout_report.json")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Scout report not found")
        
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        targets = data.get("top_targets", [])
        original_len = len(targets)
        data["top_targets"] = [t for t in targets if t.get("id") != req.issue_id]
        
        # If we actually removed something, decrement scanning count
        if len(data["top_targets"]) < original_len:
            data["total_scanned"] = max(0, data.get("total_scanned", 0) - 1)
            
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        return {"status": "success", "remaining": len(data["top_targets"])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# WebSocket Terminal — Direct Shell Web-CLI
# ---------------------------------------------------------------------------

@app.websocket("/ws/terminal")
async def terminal_ws(
    websocket: WebSocket, 
    token: str = Query(default=""),
    session_id: str = Query(default="trevor-main")
):
    """
    Real-time bash terminal over WebSocket with session persistence.
    """
    if not TERMINAL_SECRET or token != TERMINAL_SECRET:
        await websocket.close(code=4401)
        return
        
    if terminal_manager is None:
        await websocket.accept()
        await websocket.send_text("PTY Terminal not supported on this operating system architecture.")
        await websocket.close(code=1011)
        return

    await websocket.accept()

    try:
        session = await terminal_manager.get_or_create(session_id)
        session.active_clients.add(websocket)
        
        # Replay buffer to the newly connected client
        for chunk in session.output_buffer:
            await websocket.send_bytes(chunk)
            
        while True:
            # Priority: Connectivity Guard
            if websocket.client_state != WebSocketState.CONNECTED:
                break
                
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                session.pty.write(message["bytes"])
            elif "text" in message and message["text"]:
                raw = message["text"]
                try:
                    payload = json.loads(raw)
                    if payload.get("type") == "resize":
                        rows = int(payload.get("rows", 24))
                        cols = int(payload.get("cols", 80))
                        session.pty.resize(rows, cols)
                    elif payload.get("type") == "clear_buffer":
                        session.clear_buffer()
                    else:
                        session.pty.write(raw.encode())
                except (json.JSONDecodeError, ValueError):
                    session.pty.write(raw.encode())

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Terminal WS Error: {e}")
    finally:
        if 'session' in locals():
            session.active_clients.discard(websocket)
            session.last_client_at = time.time()

@app.post("/terminal/session/{session_id}/clear-buffer")
async def clear_terminal_buffer(session_id: str, token: str = Query(default="")):
    """Flushes the backend output buffer for a specific session."""
    if not TERMINAL_SECRET or token != TERMINAL_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    if terminal_manager is None:
        raise HTTPException(status_code=501, detail="Terminal manager not initialized")
    
    session = terminal_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.clear_buffer()
    return {"status": "success", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

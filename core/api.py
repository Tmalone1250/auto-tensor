import os
from dotenv import load_dotenv
load_dotenv()
import shutil
import time
import sys
import subprocess
import json
import traceback
import contextlib
import asyncio
from datetime import datetime
from typing import Optional, List, Dict

# Ensure root is in sys.path (Absolute Priority)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Body, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core.terminal import PtyManager
from core.terminal_manager import terminal_manager

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
    "provisioned_repos": [] # Local folders in workspace/
}

# --- State Management ---
REGISTRY_PATH = "core/registry.json"
APPROVALS_PATH = "logs/approvals.json"

from core.health_check import check_rate_limit
from core.skill_writer import record_mission_success
from agents.scout import SurgicalScoutV3

app = FastAPI(title="Auto-Tensor Command Bridge")

@app.on_event("startup")
async def startup_event():
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
    target_repo: str # Full HTTPS URL

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

# --- Process Orchestration ---
class ProcessManager:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.active_agent: Optional[str] = None
        self.current_task: str = "Idle"
        self.start_time: float = time.time()

    def run_agent(self, agent_name: str, target: Optional[str] = None):
        """Launches an agent script in the background."""
        if self.process and self.process.poll() is None:
            return {"error": f"Agent {self.active_agent} is already running."}
        
        script_path = os.path.join("agents", f"{agent_name}.py")
        if not os.path.exists(script_path):
            return {"error": f"Agent script {script_path} not found."}

        # Redirect output to workflow log
        log_path = os.path.join("logs", "workflow.log")
        os.makedirs("logs", exist_ok=True)
        
        log_file = open(log_path, "a", encoding="utf-8")
        log_file.write(f"\n--- [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] COMMAND DECK: STARTING {agent_name.upper()} ---\n")
        if target:
            log_file.write(f"Target: {target}\n")
        log_file.flush()

        # Command to run inside the venv (HARDCODED Linux-native resolution)
        if sys.platform == "win32":
            venv_python = "venv/Scripts/python.exe"
            if not os.path.exists(venv_python):
                venv_python = ".venv/Scripts/python.exe"
        else:
            # ENFORCED: Must use venv/bin/python for VPS stability
            venv_python = "venv/bin/python"
            if not os.path.exists(venv_python):
                # Fallback only to .venv if absolutely necessary
                venv_python = ".venv/bin/python"

        if not os.path.exists(venv_python):
            venv_python = sys.executable # Final fallback

        cmd = [venv_python, script_path]
        if target:
            cmd.append(target)

        log_file.write(f"EXEC CMD: {' '.join(cmd)}\n")
        log_file.flush()

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=log_file,
                text=True,
                bufsize=1
            )
            self.active_agent = agent_name
            self.current_task = f"Executing {agent_name} mission..."
            
            # Sync with Global State
            global SYSTEM_STATE
            SYSTEM_STATE["active_agent"] = agent_name.capitalize()
            SYSTEM_STATE["is_running"] = True
            
            return {"status": "started", "agent": agent_name}
        except Exception as e:
            error_msg = f"FAILED TO START AGENT: {str(e)}"
            log_file.write(f"[CRITICAL] {error_msg}\n")
            log_file.write(traceback.format_exc())
            log_file.flush()
            return {"error": error_msg}

    def stop_agent(self):
        """Terminates the active agent process."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            
            self.process = None
            self.active_agent = None
            self.current_task = "Idle (Terminated)"

            # Sync with Global State
            global SYSTEM_STATE
            SYSTEM_STATE["active_agent"] = "None"
            SYSTEM_STATE["is_running"] = False

            return {"status": "terminated"}
        return {"error": "No active agent to stop."}

    def get_info(self):
        """Checks process status and returns metadata."""
        is_running = self.process is not None and self.process.poll() is None
        if not is_running:
            self.active_agent = None
            self.current_task = "Idle"
        
        return {
            "is_running": is_running,
            "active_agent": self.active_agent or "None",
            "current_task": self.current_task
        }

# Global Process Manager
pm = ProcessManager()

def run_scout_sync(url: str):
    """Refactored Scout Orchestrator: Direct import with real-time log redirection."""
    global SYSTEM_STATE
    SYSTEM_STATE["active_agent"] = "Scout"
    SYSTEM_STATE["is_running"] = True
    SYSTEM_STATE["current_repo"] = url
    
    log_path = os.path.join("logs", "scout.log")
    os.makedirs("logs", exist_ok=True)
    
    try:
        with open(log_path, "a", encoding="utf-8") as log_file:
            with contextlib.redirect_stdout(log_file), contextlib.redirect_stderr(log_file):
                print(f"\n--- [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INTELLIGENCE NODE: STARTING SURGICAL SCOUT V3 ---")
                print(f"Target: {url}")
                sys.stdout.flush()
                
                scout = SurgicalScoutV3(config_path="config.yaml")
                scout.scan(target_repo=url)
                
                print(f"--- [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INTELLIGENCE NODE: MISSION COMPLETE ---")
                sys.stdout.flush()
    except Exception:
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"\n[CRITICAL ERROR] Scout crash detected:\n")
            traceback.print_exc(file=log_file)
            log_file.flush()
    finally:
        SYSTEM_STATE["active_agent"] = "None"
        SYSTEM_STATE["is_running"] = False

def run_refine_sync():
    """Blueprint Refinement Orchestrator: Re-generates failed strategies in place."""
    global SYSTEM_STATE
    SYSTEM_STATE["active_agent"] = "Scout (Refining)"
    SYSTEM_STATE["is_running"] = True
    
    log_path = os.path.join("logs", "scout.log")
    os.makedirs("logs", exist_ok=True)
    
    try:
        with open(log_path, "a", encoding="utf-8") as log_file:
            with contextlib.redirect_stdout(log_file), contextlib.redirect_stderr(log_file):
                print(f"\n--- [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INTELLIGENCE NODE: REFINING FAILED BLUEPRINTS ---")
                sys.stdout.flush()
                
                scout = SurgicalScoutV3(config_path="config.yaml")
                scout.refine_blueprints()
                
                print(f"--- [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INTELLIGENCE NODE: REFINEMENT COMPLETE ---")
                sys.stdout.flush()
    except Exception:
        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"\n[CRITICAL ERROR] Refinement crash detected:\n")
            traceback.print_exc(file=log_file)
            log_file.flush()
    finally:
        SYSTEM_STATE["active_agent"] = "None"
        SYSTEM_STATE["is_running"] = False

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
    """Returns GitHub Quota, Uptime, and Process Status."""
    rate_limit = check_rate_limit()
    uptime_seconds = int(time.time() - pm.start_time)
    
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    # Use Global SYSTEM_STATE for accurate UI reporting
    active_agent = SYSTEM_STATE["active_agent"]
    is_running = SYSTEM_STATE["is_running"]
    current_task = f"Executing {active_agent} mission..." if is_running else "Idle"

    return {
        "github_status": rate_limit,
        "miner_uptime": uptime_str,
        "active_agent": active_agent,
        "is_running": is_running,
        "current_task": current_task,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/agent/run")
def run_agent(request: AgentRequest):
    """Command Deck Trigger: Starts an agent mission."""
    return pm.run_agent(request.agent_name, request.target)

@app.post("/agent/stop")
def stop_agent():
    """Command Deck Trigger: Terminates active agent."""
    return pm.stop_agent()

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

@app.post("/repo/provision")
async def provision_repository(request: ProvisionRequest):
    """
    Manual Hub Step: Forks, Branches, and Clones the target repo.
    Decoupled from Coder Agent for human-in-the-loop control.
    """
    url = request.target_repo.strip()
    if not url.startswith("https://github.com/"):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")

    folder = get_provision_folder(url)
    workspace_path = os.path.join("workspace", folder)
    
    # 1. Dirty Workspace Wipe
    if os.path.exists(workspace_path):
        shutil.rmtree(workspace_path)
    
    token = os.getenv("GITHUB_KEY")
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    
    # 2. Fork
    parts = url.rstrip("/").split("/")
    owner, repo_name = parts[-2], parts[-1].replace(".git", "")
    fork_api_url = f"https://api.github.com/repos/{owner}/{repo_name}/forks"
    
    try:
        res = requests.post(fork_api_url, headers=headers, timeout=30)
        if res.status_code not in [201, 202]:
            raise HTTPException(status_code=500, detail=f"Fork failed: {res.status_code} - {res.text}")
        
        fork_data = res.json()
        fork_url = fork_data.get("html_url")
        fork_owner = fork_data.get("owner", {}).get("login")
        
        # 3. Polling Guard
        if not await poll_fork_status(fork_url, headers):
             raise HTTPException(status_code=500, detail="Fork provision timed out on GitHub.")

        # 4. Create Branch 'auto-tensor-dev'
        repo_info = requests.get(f"https://api.github.com/repos/{fork_owner}/{repo_name}", headers=headers).json()
        default_branch = repo_info.get("default_branch", "main")
        
        ref_url = f"https://api.github.com/repos/{fork_owner}/{repo_name}/git/refs/heads/{default_branch}"
        ref_res = requests.get(ref_url, headers=headers).json()
        base_sha = ref_res.get("object", {}).get("sha")
        
        if not base_sha:
            raise HTTPException(status_code=500, detail=f"Could not find SHA for {default_branch} on fork.")

        branch_name = "auto-tensor-dev"
        create_br_url = f"https://api.github.com/repos/{fork_owner}/{repo_name}/git/refs"
        br_res = requests.post(create_br_url, headers=headers, json={"ref": f"refs/heads/{branch_name}", "sha": base_sha})
        # 201 Created or 422 Unprocessable if branch exists
        if br_res.status_code not in [201, 422]:
            raise HTTPException(status_code=500, detail=f"Branch creation failed: {br_res.text}")

        # 5. Clone fork's branch
        auth_clone_url = fork_url.replace("https://github.com/", f"https://{token}@github.com/")
        os.makedirs("workspace", exist_ok=True)
        subprocess.run(["git", "clone", "-b", branch_name, auth_clone_url, workspace_path], check=True, capture_output=True)
        
        # 6. Update State & Persistence
        global SYSTEM_STATE
        if folder not in SYSTEM_STATE["provisioned_repos"]:
            SYSTEM_STATE["provisioned_repos"].append(folder)
            
        registry = load_json(REGISTRY_PATH, {"repos": []})
        for r in registry["repos"]:
            if r["html_url"] == url:
                r["provisioned"] = True
                r["provisioned_at"] = datetime.now().isoformat()
        save_json(REGISTRY_PATH, registry)
        
        return {"status": "success", "folder": folder, "branch": branch_name}

    except subprocess.CalledProcessError as e:
        clean_err = e.stderr.decode().replace(token, "****") if token else e.stderr.decode()
        raise HTTPException(status_code=500, detail=f"Clone failed: {clean_err}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Provisioning error: {str(e)}")

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
    """Triggers the Scout agent on a specific repository URL."""
    url = request.url.strip()
    if not url.startswith("https://github.com/"):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
        
    background_tasks.add_task(run_scout_sync, url)
    return {"status": "started", "agent": "scout", "target": url}

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

@app.post("/agent/retry")
def retry_agent():
    """Restarts the last active agent with its previous target."""
    info = pm.get_info()
    if not info["active_agent"] or info["active_agent"] == "None":
        # Check logs for last agent
        return {"error": "No previous agent found to retry."}
    
    return pm.run_agent(info["active_agent"])

@app.post("/scout/promote")
def promote_issue(background_tasks: BackgroundTasks, issue: Dict = Body(...)):
    """Promotes a scouted issue with a fix strategy to the Coder agent."""
    repo = issue.get("repo")
    title = issue.get("title")
    strategy = issue.get("strategy", "No strategy provided.")
    
    if not repo:
        raise HTTPException(status_code=400, detail="Missing repo in issue data")
    
    repro_cmd = issue.get("repro_cmd")
    fix_cmd = issue.get("fix_cmd")
    
    if not repro_cmd or not fix_cmd or "# Missing" in repro_cmd or "# Missing" in fix_cmd:
        raise HTTPException(
            status_code=400, 
            detail="Mission malformed: Scout failed to provide actionable repro_cmd or fix_cmd."
        )
    
    try:
        # Store promotion in a directive file for the Coder to pick up
        directive = {
            "mission_id": f"MISSION-{int(time.time())}",
            "target_repo": issue.get("target_repo") or repo,
            "title": title,
            "body": issue.get("body", "No body context provided."),
            "strategy": strategy,
            "repro_cmd": issue.get("repro_cmd"),
            "fix_cmd": issue.get("fix_cmd"),
            "timestamp": datetime.now().isoformat()
        }
        
        mission_params_path = "logs/mission_parameters.json"
        save_json(mission_params_path, directive)
        save_json("logs/current_mission.json", issue)
        
        # Log promotion
        with open(os.path.join("logs", "workflow.log"), "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] [API] Issue promoted to Coder: {title[:50]}...\n")

        # Trigger Coder in background to ensure zero UI lag
        background_tasks.add_task(pm.run_agent, "coder", target=repo)
        
        return {"status": "success", "msg": "Mission promoted. Coder initializing."}
        
    except Exception as e:
        error_log = os.path.join("logs", "workflow.log")
        with open(error_log, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] [CRITICAL] Promotion failed: {str(e)}\n")
            traceback.print_exc(file=f)
        raise HTTPException(status_code=500, detail=f"Promotion failed: {str(e)}")

@app.get("/scout/report")
def get_scout_report():
    """Returns the latest scout report (intelligence results)."""
    report_path = os.path.join("logs", "scout_report.json")
    if not os.path.exists(report_path):
        return {"error": "No scout report found."}
    
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

@app.post("/scout/refine")
def refine_scout_report(background_tasks: BackgroundTasks):
    """Triggers refinement of failed strategies in the current report."""
    background_tasks.add_task(run_refine_sync)
    return {"status": "started", "agent": "scout", "task": "refining"}

@app.get("/coder/diff")
def get_coder_diff():
    """Returns the current diff generated by the Coder."""
    diff_path = os.path.join("logs", "coder_diff.md")
    if not os.path.exists(diff_path):
        return {"diff": "No active diff found."}
    
    try:
        with open(diff_path, "r", encoding="utf-8") as f:
            return {"diff": f.read()}
    except Exception as e:
        return {"error": str(e)}

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

    await websocket.accept()

    try:
        session = await terminal_manager.get_or_create(session_id)
        session.active_clients.add(websocket)
        
        # Replay buffer to the newly connected client
        for chunk in session.output_buffer:
            await websocket.send_bytes(chunk)
            
        while True:
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
    
    session = terminal_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.clear_buffer()
    return {"status": "success", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

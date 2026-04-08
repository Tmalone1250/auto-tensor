import os
import shutil
import time
import sys
import subprocess
import json
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure root is in sys.path so we can import core.health_check
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.health_check import check_rate_limit

app = FastAPI(title="Auto-Tensor Command Bridge")

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

# --- State Management ---
REGISTRY_PATH = os.path.join("core", "registry.json")
APPROVALS_PATH = os.path.join("logs", "approvals.json")

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

        # Command to run inside the venv
        venv_python = os.path.join(".venv", "bin", "python")
        if not os.path.exists(venv_python):
             venv_python = "python3" # Fallback

        cmd = [venv_python, script_path]
        if target:
            cmd.append(target)

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
            return {"status": "started", "agent": agent_name}
        except Exception as e:
            return {"error": str(e)}

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

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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

    info = pm.get_info()
    return {
        "github_status": rate_limit,
        "miner_uptime": uptime_str,
        "active_agent": info["active_agent"],
        "is_running": info["is_running"],
        "current_task": info["current_task"],
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
def scan_repository(request: RepoRequest):
    """Triggers the Scout agent on a specific repository URL."""
    url = request.url.strip()
    if not url.startswith("https://github.com/"):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
        
    # We pass the URL as the target to the scout
    return pm.run_agent("scout", target=url)

# --- Approvals Workflow ---
@app.get("/approvals")
def get_approvals():
    """Returns the list of pending approvals."""
    return load_json(APPROVALS_PATH, {"pending": []})

@app.post("/approvals/action")
def approval_action(action: ApprovalAction):
    """Executes a stage in the approval workflow."""
    # Placeholder for actual git/github orchestration
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
def promote_issue(issue: Dict = Body(...)):
    """Promotes a scouted issue with a fix strategy to the Coder agent."""
    repo = issue.get("repo")
    title = issue.get("title")
    strategy = issue.get("strategy", "No strategy provided.")
    
    if not repo:
        raise HTTPException(status_code=400, detail="Missing repo in issue data")
    
    # Store promotion in a directive file for the Coder to pick up
    directive = {
        "repo": repo,
        "title": title,
        "strategy": strategy,
        "timestamp": datetime.now().isoformat()
    }
    save_json(os.path.join("logs", "mission_parameters.json"), directive)
    save_json(os.path.join("logs", "current_mission.json"), issue)
    
    # Trigger Coder immediately
    return pm.run_agent("coder", target=repo)

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
    """Archives the current workflow log and starts a new one."""
    log_path = os.path.join("logs", "workflow.log")
    archive_dir = os.path.join("logs", "archive")
    
    try:
        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if os.path.exists(log_path):
            archive_path = os.path.join(archive_dir, f"workflow_{timestamp}.log")
            shutil.move(log_path, archive_path)
            
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"--- [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] LOGS CLEARED BY OPERATOR ---\n")
            
        return {"status": "success", "archived_as": f"workflow_{timestamp}.log"}
    except Exception as e:
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

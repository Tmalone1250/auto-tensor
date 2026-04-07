from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import time
from datetime import datetime
import sys

# Ensure root is in sys.path so we can import core.health_check
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.health_check import check_rate_limit

app = FastAPI(title="Auto-Tensor Command Bridge")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Vite default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()
ACTIVE_AGENT = "Scout" # Placeholder for state tracking

@app.get("/status")
def get_status():
    """Returns GitHub Rate Limit, Miner Uptime, and Active Agent."""
    rate_limit = check_rate_limit()
    uptime_seconds = int(time.time() - START_TIME)
    
    # Format uptime nicely
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return {
        "github_status": rate_limit,
        "miner_uptime": uptime_str,
        "active_agent": ACTIVE_AGENT,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/audit")
def get_audit():
    """Returns the contents of logs/simulation_audit.md as a JSON string."""
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
def get_logs():
    """Streams the last 50 lines of the workflow log."""
    log_path = os.path.join("logs", "workflow.log")
    
    # Initialize log if it doesn't exist
    if not os.path.exists(log_path):
        os.makedirs("logs", exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] WAR ROOM: Workflow logger initialized.\n")

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return {"logs": [line.strip() for line in lines[-50:]]}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # When running directly, we use the module name to support reload if needed
    uvicorn.run(app, host="0.0.0.0", port=8000)

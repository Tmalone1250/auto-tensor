import os
import requests
import subprocess
from functools import wraps

def tool_github_fork(repo_full_name: str) -> str:
    """Uses GITHUB_KEY to fork a target repository into the scoped namespace."""
    github_pat = os.getenv("GITHUB_KEY")
    if not github_pat:
        return "Error: GITHUB_KEY environment variable is missing natively."
    
    headers = {
        "Authorization": f"token {github_pat}",
        "Accept": "application/vnd.github.v3+json"
    }
    repo_clean = repo_full_name.replace("https://github.com/", "").replace(".git", "").strip("/")
    url = f"https://api.github.com/repos/{repo_clean}/forks"
    
    try:
        response = requests.post(url, headers=headers, timeout=30)
        if response.status_code in [201, 202]:
            fork_data = response.json()
            return f"Successfully forked target. Remote fork URL: {fork_data.get('html_url')}"
        return f"Error: Fork initialization failed natively with {response.status_code}: {response.text}"
    except Exception as e:
        return f"Error: {e}"

def tool_github_clone(repo_url: str) -> str:
    """Clones a repository dynamically into workspace/ structural bound."""
    github_pat = os.getenv("GITHUB_KEY")
    if github_pat and "github.com" in repo_url and not "@github.com" in repo_url:
        auth_url = repo_url.replace("https://github.com/", f"https://{github_pat}@github.com/")
    else:
        auth_url = repo_url

    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "").lower()
    workspace_path = os.path.join("workspace", repo_name)
    
    if os.path.exists(workspace_path):
        return f"Repository already natively cloned at {workspace_path}"
        
    try:
        os.makedirs("workspace", exist_ok=True)
        result = subprocess.run(["git", "clone", auth_url, workspace_path], capture_output=True, text=True)
        if result.returncode != 0:
            return f"Error cloning repository bounds: {result.stderr}"
        return f"Successfully cloned structurally into {workspace_path}."
    except Exception as e:
        return f"Error: {e}"

def tool_github_create_branch(repo_path: str, branch_name: str) -> str:
    """Readies the repository schema struct for manual tracking staging."""
    if not os.path.exists(repo_path):
         return f"Error: Target path {repo_path} does not securely exist."
    cmd = f"git checkout -b {branch_name}"
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=repo_path)
        if result.returncode != 0:
            return f"Error creating branch isolation: {result.stderr}"
        return f"Branch {branch_name} explicitly generated and checked out safely."
    except Exception as e:
        return f"Error: {e}"

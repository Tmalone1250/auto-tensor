import os
import subprocess
import requests
import json

def tool_get_repo_map(max_depth: int = 3, repo_path: str = ".") -> str:
    cmd = ["find", repo_path, "-maxdepth", str(max_depth), "-not", "-path", "*/.git/*", "-not", "-path", "*/__pycache__/*", "-not", "-path", "*/node_modules/*"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"Error mapping repo: {e}"

def tool_grep_codebase(regex_pattern: str, repo_path: str = ".") -> str:
    cmd = ["grep", "-rnE", regex_pattern, repo_path, "--exclude-dir=.git", "--exclude-dir=__pycache__", "--exclude-dir=node_modules"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout[:5000]
    except Exception as e:
        return f"Error searching codebase: {e}"

def tool_identify_cli(repo_path: str = ".") -> str:
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
            if "/" not in file.replace(repo_path, "").strip("/"): score += 2 
            scored.append({"file": file, "confidence": score})
            
        scored.sort(key=lambda x: x["confidence"], reverse=True)
        return json.dumps(scored, indent=2)
    except Exception as e:
        return f"Error identifying CLI: {e}"

def tool_summarize_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        return f"Error: File {file_path} not found"
        
    cmd = ["grep", "-nE", "^class |^ *def |^const |^function ", file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"Error summarizing file: {e}"

def tool_rank_issues(issues_list: list, target_repo: str) -> list:
    """Isolates the calculate_delta_score ranking heuristics and reduces tokens."""
    for issue in issues_list:
        score = 5
        body = (issue.get("body") or "").lower()
        title = (issue.get("title") or "").lower()
        author_assoc = issue.get("author_association", "NONE")
        
        if "any" in body or "missing interface" in body or "interface" in body:
            score += 3
        
        labels_list = issue.get("labels", [])
        if not isinstance(labels_list, list): labels_list = []
        labels = [l.get("name", "").lower() for l in labels_list if isinstance(l, dict)]
        
        structural_labels = {"performance": 3, "logic": 3, "refactor": 2, "bug": 2, "security": 2}
        for label, boost in structural_labels.items():
            if label in labels: score += boost
            
        repo_clean = target_repo.replace("https://github.com/", "").replace("http://github.com/", "").replace(".git", "").strip("/")
        repo_base = repo_clean.split("/")[-1].lower() if "/" in repo_clean else repo_clean.lower()
        is_premium = (repo_base == "gittensor")
        if author_assoc in ["OWNER", "MEMBER", "COLLABORATOR"] or is_premium:
            score = int(score * 1.66)
            issue["multiplier"] = 1.66
        else:
            issue["multiplier"] = 1.0
            
        if any(kw in title for kw in ["typo", "docs", "readme", "comment"]):
             score -= 4
             
        issue["delta_score"] = min(10, max(1, score))
        
    return sorted(issues_list, key=lambda x: x.get("delta_score", 0), reverse=True)

def tool_fetch_issues(repo: str) -> list:
    """Network-level issue discovery stripped natively out of the core loops."""
    github_pat = os.getenv("GITHUB_KEY")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if github_pat:
        headers["Authorization"] = f"token {github_pat}"
    
    repo_clean = repo.replace("https://github.com/", "").replace("http://github.com/", "").replace(".git", "").strip("/")
    url = f"https://api.github.com/repos/{repo_clean}/issues"
    params = {"state": "open", "sort": "created", "direction": "desc", "per_page": 30}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return [i for i in response.json() if not i.get("assignee") and "pull_request" not in i]
    return []

def tool_grep_context(pattern: str, file_path: str) -> str:
    """Returns target line with bounded +/- 10 lines zeroed padding."""
    if not os.path.exists(file_path):
        return f"Error: Identity File {file_path} not natively found"
        
    cmd = ["grep", "-rnE", "-C", "10", pattern, file_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return "Pattern search not found or fault occurred."
        return result.stdout[:8000]
    except Exception as e:
        return f"Error executing grep explicit context: {e}"

def tool_find_file(filename: str, repo_path: str = ".") -> str:
    """Locates explicit file definitions inside a structural map."""
    if not os.path.exists(repo_path):
        return f"Error: Repository target path {repo_path} dynamically missing."
        
    cmd = ["find", repo_path, "-name", filename]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"Error executing locate loop: {e}"

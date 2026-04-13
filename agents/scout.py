import os
import sys
import json
import yaml
import requests
import time
from core.base_agent import BaseAgent
from core.tools.common import reflect_and_memorize, json_safe_parse
from core.tools.scout_ops import tool_rank_issues, tool_get_repo_map

MISSION_PARAMS = "logs/mission_parameters.json"
REGISTRY_PATH = "core/registry.json"

class ScoutAgent(BaseAgent):
    def __init__(self, config_path: str = "config.yaml"):
        super().__init__("scout")
        try:
            with open(config_path, "r") as f:
                self.config = yaml.safe_load(f)
        except Exception:
            self.config = {}
        
        self.github_pat = os.getenv("GITHUB_KEY")
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if self.github_pat:
            self.headers["Authorization"] = f"token {self.github_pat}"
            
        self.watchlist = self.load_watchlist()

    def load_watchlist(self) -> list:
        if os.path.exists(REGISTRY_PATH):
            try:
                with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return [repo["full_name"] for repo in data.get("repos", [])]
            except Exception as e:
                print(f"Error loading registry: {e}")
        return self.config.get("repo_watchlist", [])

    def fetch_issues(self, repo: str) -> list:
        url = f"https://api.github.com/repos/{repo}/issues"
        params = {"state": "open", "sort": "created", "direction": "desc", "per_page": 30}
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            return [i for i in response.json() if not i.get("assignee") and "pull_request" not in i]
        return []

    def scan(self, target_repo: str = None):
        if os.path.exists(MISSION_PARAMS): os.remove(MISSION_PARAMS)
        
        repos_to_scan = [target_repo] if target_repo else self.watchlist
        all_results = []
        
        for repo in repos_to_scan:
            print(f"[Bored Scout]: Scouting {repo}...")
            repo_map = tool_get_repo_map(max_depth=2, repo_path=f"workspace/{repo.split('/')[-1]}")
            
            issues = self.fetch_issues(repo)
            ranked_issues = tool_rank_issues(issues, target_repo=repo)
            
            if ranked_issues:
                all_results.append({
                    "repo": repo,
                    "top_issue": ranked_issues[0]
                })

        # BaseAgent Routing directly maps architecture
        if all_results:
            top_target = all_results[0]
            context = f"Repo Map:\n{repo_map[:1000]}\n\nTop Issue:\n{top_target['top_issue'].get('title')}: {top_target['top_issue'].get('body')[:500]}"
            print("[Bored Scout]: Invoking Router-Tool Logic...")
            
            # The system prompts deterministically routes JSON payloads
            response = self.route(context, state="DECISION_REQUIRED")
            parsed = json_safe_parse(response)
            
            entry = parsed.get("entry_point", "cli.py") if isinstance(parsed, dict) else "cli.py"

            with open(MISSION_PARAMS, "w") as f:
                json.dump({"mission_id": "V3-AUDIT", "target_repo": top_target["repo"], "entry_point": entry}, f, indent=2)

            # Reflection Mandate execution
            reflect_and_memorize("scout", top_target["repo"], entry, f"python3 {entry} help")
            
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", help="Target repository")
    args = parser.parse_args()

    agent = ScoutAgent()
    agent.scan(target_repo=args.repo)

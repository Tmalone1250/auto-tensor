import os
import sys
import json
import yaml
from core.base_agent import BaseAgent
from core.tools.scout_ops import tool_get_repo_map, tool_fetch_issues, tool_rank_issues

MISSION_PARAMS = "logs/mission_parameters.json"
REPORT_PATH = "logs/scout_report.json"
REGISTRY_PATH = "core/registry.json"

class ScoutAgent(BaseAgent):
    def __init__(self, config_path: str = "config.yaml"):
        super().__init__("scout")
        try:
            with open(config_path, "r") as f:
                self.config = yaml.safe_load(f)
        except Exception:
            self.config = {}
        
        self.watchlist = self.load_watchlist()

    def load_watchlist(self) -> list:
        if os.path.exists(REGISTRY_PATH):
            try:
                with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return [repo["full_name"] for repo in data.get("repos", [])]
            except Exception as e:
                pass
        return self.config.get("repo_watchlist", [])

    def scan(self, target_repo: str = None):
        if os.path.exists(MISSION_PARAMS): os.remove(MISSION_PARAMS)
        repos_to_scan = [target_repo] if target_repo else self.watchlist
        
        for repo in repos_to_scan:
            print(f"[Bored Scout]: Grounding into {repo}...")
            repo_map = tool_get_repo_map(max_depth=2, repo_path=f"workspace/{repo.split('/')[-1]}")
            issues = tool_fetch_issues(repo)
            ranked_issues = tool_rank_issues(issues, target_repo=repo)
            
            top_targets = []
            
            # Restoring Top-3 Focus
            for issue in ranked_issues[:3]:
                context = (f"Target Repository: {repo}\n"
                           f"Repo Map:\n{repo_map[:1000]}\n\n"
                           f"Target Issue:\n{issue.get('title')}: {issue.get('body')[:500]}\n\n"
                           f"Goal: Use tools to discover the codebase and formulate a blueprint. "
                           f"Output FINISH when you have args: strategy, repro_cmd, and fix_cmd.")
                
                print(f"[Bored Scout]: Analyzing Issue #{issue.get('number')} via Heartbeat...")
                final_state = self.execute_mission(context)
                
                args = final_state.get("args", {}) if final_state else {}
                
                top_targets.append({
                    "id": issue.get("number") or issue.get("id"),
                    "title": issue.get("title"),
                    "body": issue.get("body"),
                    "strategy": args.get("strategy", "Standard heuristic approach"),
                    "repro_cmd": args.get("repro_cmd", "ls -l"),
                    "fix_cmd": args.get("fix_cmd", "ls -l"),
                    "multiplier": issue.get("delta_score", 1.0),
                    "repo": repo
                })
            
            # Assemble API payload
            report_data = {
                "repo": repo,
                "total_scanned": len(ranked_issues),
                "top_targets": top_targets
            }
            
            os.makedirs("logs", exist_ok=True)
            with open(REPORT_PATH, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)
                
            print(f"[Bored Scout]: Report generated successfully inside {REPORT_PATH}.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", help="Target repository")
    args = parser.parse_args()
    
    agent = ScoutAgent()
    agent.scan(target_repo=args.repo)

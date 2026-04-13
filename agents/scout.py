import os
import sys
import json
import yaml
from core.base_agent import BaseAgent
from core.tools.scout_ops import tool_get_repo_map, tool_fetch_issues, tool_rank_issues

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
        all_results = []
        
        for repo in repos_to_scan:
            print(f"[Bored Scout]: Grounding into {repo}...")
            repo_map = tool_get_repo_map(max_depth=2, repo_path=f"workspace/{repo.split('/')[-1]}")
            issues = tool_fetch_issues(repo)
            ranked_issues = tool_rank_issues(issues, target_repo=repo)
            
            if ranked_issues:
                all_results.append({"repo": repo, "top_issue": ranked_issues[0], "map": repo_map})

        if all_results:
            top_target = all_results[0]
            context = f"Target Repository: {top_target['repo']}\nRepo Map:\n{top_target['map'][:1000]}\n\nTop Issue:\n{top_target['top_issue'].get('title')}: {top_target['top_issue'].get('body')[:500]}\n\nGoal: Audit discovery using tools and output FINISH when entry_point and fix_cmd are known."
            
            # Start V3 Heartbeat Iteration
            final_state = self.execute_mission(context)
            
            entry = final_state.get("args", {}).get("entry_point", "cli.py") if final_state else "cli.py"
            
            with open(MISSION_PARAMS, "w") as f:
                json.dump({"mission_id": "V3-HEARTBEAT", "target_repo": top_target["repo"], "entry_point": entry}, f, indent=2)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", help="Target repository")
    args = parser.parse_args()
    
    agent = ScoutAgent()
    agent.scan(target_repo=args.repo)

import os
import json
import yaml
from core.base_agent import BaseAgent
from core.tools.scout_ops import tool_fetch_issues, tool_rank_issues

REPORT_PATH = "logs/scout_report.json"
REGISTRY_PATH = "core/registry.json"

class MaggieAgent(BaseAgent):
    def __init__(self, config_path: str = "config.yaml"):
        super().__init__("maggie")
        try:
            with open(config_path, "r") as f:
                self.config = yaml.safe_load(f)
        except Exception:
            self.config = {}
            
        self.watchlist = self.load_watchlist()

        # Hard-wire the Identity Prompt
        self.system_prompt = (
            "You are Maggie, an elite Auto-Tensor intelligence sniper. Your pug-like persistence is your strength. "
            "You do not stop until you have identified the exact line number of the bug and verified the CLI command needed to fix it. "
            "Exclusively output valid JSON. Use valid Git/Search tool loops."
        )

    def _load_tools(self):
        """Override BaseAgent tool loading to inject the raw V4 registry native ops."""
        from core.tools import v4_tool_registry
        self.tools = v4_tool_registry

    def load_watchlist(self) -> list:
        if os.path.exists(REGISTRY_PATH):
            try:
                with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return [repo["full_name"] for repo in data.get("repos", [])]
            except Exception:
                pass
        return self.config.get("repo_watchlist", [])

    def scan(self, target_repo: str = None):
        repos_to_scan = [target_repo] if target_repo else self.watchlist
        
        for repo in repos_to_scan:
            print(f"[Maggie Intelligence]: Sniping target repository {repo}...")
            
            issues = tool_fetch_issues(repo)
            ranked_issues = tool_rank_issues(issues, target_repo=repo)
            
            top_targets = []
            
            # Top 3 Focus
            for issue in ranked_issues[:3]:
                context = (f"Target Repository: {repo}\n"
                           f"Target Issue:\n{issue.get('title')}: {issue.get('body')[:1000]}\n\n"
                           f"Goal: Fork, clone, branch ('maggie-fix'), and discover the codebase explicitly to formulate a perfectly grounded execution strategy. "
                           f"Output FINISH when you have identified the precise files and generated a Surgical Briefing. "
                           f"Provide args: strategy, repro_cmd, and fix_cmd. The fix_cmd must be incredibly explicit, like 'Fix index.html:7. Verify with: npm run build'.")
                
                print(f"[Maggie Action]: Engaging Issue #{issue.get('number')} through the persistence loop...")
                final_state = self.execute_mission(context)
                
                args = final_state.get("args", {}) if final_state else {}
                
                top_targets.append({
                    "id": issue.get("number") or issue.get("id"),
                    "title": issue.get("title"),
                    "body": issue.get("body"),
                    "strategy": args.get("strategy", "Surgical search aborted without resolution"),
                    "repro_cmd": args.get("repro_cmd", "Not provided"),
                    "fix_cmd": args.get("fix_cmd", "Not provided"),
                    "multiplier": issue.get("delta_score", 1.0),
                    "repo": repo
                })
            
            report_data = {
                "repo": repo,
                "total_scanned": len(ranked_issues),
                "top_targets": top_targets
            }
            
            os.makedirs("logs", exist_ok=True)
            with open(REPORT_PATH, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2)
                
            print(f"[Maggie Diagnostics]: Surgical Briefing locked and loaded safely into {REPORT_PATH}.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", help="Target repository scope")
    args = parser.parse_args()
    
    agent = MaggieAgent()
    agent.scan(target_repo=args.repo)

import os
from dotenv import load_dotenv
load_dotenv()
import sys
import requests
import yaml
import time
import json
from typing import List, Dict, Any

# Ensure root is in sys.path so we can import core modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MISSION_PARAMS = "logs/mission_parameters.json"

class SurgicalScoutV3:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        
        self.github_pat = os.getenv("GITHUB_KEY")
        if not self.github_pat:
            print("[CRITICAL] Miner PAT not found. Contribution eligibility at risk. Rate limits will be very tight.")
            sys.stdout.flush()

        self.registry_path = "core/registry.json"
        self.watchlist = self.load_watchlist()
        self.scout_settings = self.config.get("scout_settings", {})
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.github_pat:
            self.headers["Authorization"] = f"token {self.github_pat}"
        else:
            # Adjust stealth threshold for unauthenticated sessions
            self.scout_settings["stealth_threshold"] = 5

    def load_watchlist(self) -> List[str]:
        """Loads repository full names from core/registry.json."""
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return [repo["full_name"] for repo in data.get("repos", [])]
            except Exception as e:
                print(f"Error loading registry: {e}")
                sys.stdout.flush()
        return self.config.get("repo_watchlist", [])

    def check_rate_limit(self, response: requests.Response):
        remaining = int(response.headers.get("X-RateLimit-Remaining", 1000))
        if remaining < self.scout_settings.get("stealth_threshold", 100):
            sleep_time = self.scout_settings.get("sleep_seconds", 60)
            print(f"Stealth Protocol: Rate limit low ({remaining}). Sleeping for {sleep_time}s...")
            sys.stdout.flush()
            time.sleep(sleep_time)

    def fetch_issues(self, repo: str) -> List[Dict[Any, Any]]:
        """Fetches recent unassigned issues without restrictive label filters."""
        url = f"https://api.github.com/repos/{repo}/issues"
        params = {
            "state": "open",
            "sort": "created",
            "direction": "desc",
            "per_page": 50 # Broad fetch for variety
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        self.check_rate_limit(response)
        
        if response.status_code == 200:
            all_issues = response.json()
            # Filter for unassigned and exclude Pull Requests
            filtered = [
                i for i in all_issues 
                if not i.get("assignee") and "pull_request" not in i
            ]
            return filtered
        else:
            print(f"Error fetching issues for {repo}: {response.status_code}")
            sys.stdout.flush()
            return []

    def calculate_delta_score(self, issue: Dict[Any, Any]) -> int:
        score = 5 # Base score
        body = (issue.get("body") or "").lower()
        title = (issue.get("title") or "").lower()
        author_assoc = issue.get("author_association", "NONE")
        
        # Type Hardening Prioritization
        if "any" in body or "missing interface" in body or "interface" in body:
            score += 3
        
        # Priority labels (Structural Focus v2.4 - Gittensor Quality Gate)
        labels = [l["name"].lower() for l in issue.get("labels", [])]
        # Performance/Logic/Bug carry the highest reward potential for AST Density
        structural_labels = {
            "performance": 3,
            "logic": 3,
            "refactor": 2,
            "bug": 2,
            "security": 2
        }
        for label, boost in structural_labels.items():
            if label in labels:
                score += boost
            
        # Bounty Hunter v2.4: Maintainer Multiplier (1.66x)
        maintainer_roles = ["OWNER", "MEMBER", "COLLABORATOR"]
        if author_assoc in maintainer_roles:
            score = int(score * 1.66)
            issue["multiplier"] = 1.66
        else:
            issue["multiplier"] = 1.0
            
        # Code Density Cap: Ensure we don't pick fluff
        if any(kw in title for kw in ["typo", "docs", "readme", "comment"]):
             score -= 4

        return min(10, max(1, score))

    def categorize(self, issue: Dict[Any, Any]) -> str:
        labels = [l["name"].lower() for l in issue.get("labels", [])]
        if "performance" in labels or "p1" in labels:
            return "Performance"
        if "a11y" in labels or "ui" in labels or "interface" in labels:
            return "UI"
        return "DX"

    def ingest_docs(self, targets: List[Dict]):
        """Finds and ingests relevant coding documentation for top targets."""
        print(f"[Bored Scout]: Doc-Sourcing active. Searching for technical context...")
        sys.stdout.flush()
        from core.llm import LlmClient
        llm = LlmClient()
        
        for target in targets:
            query = f"{target['repo']} {target['title']} documentation"
            target["doc_query"] = query
            print(f"  Target: {target['title']} -> Query: {query}")
            sys.stdout.flush()

        return targets

    def _get_batch_prompt(self, targets: List[Dict]) -> str:
        persona_note = "You are a DevOps Engineer specializing in Systems Reliability. Your priority is Gittensor Reward Maximization. Identify the top highest-priority, structural-fix candidates."
        issues_text = ""
        for t in targets:
            issues_text += f"---\nID: {t['id']}\nRepo: {t['repo']}\nTitle: {t['title']}\nBody: {t.get('body', '')[:600]}\n"
        
        return (
            f"{persona_note}\n\n"
            f"Propose a concise, structural fix strategy for each of the following GitHub issues.\n\n"
            f"{issues_text}\n"
            "TECH-STACK MANDATE: Identify if the project is Node.js, Python, or Rust. Use language-specific commands:\n"
            "- Node.js: 'npm install' | 'node ...' or 'npm run ...'\n"
            "- Python: 'python3 -m pip install -e .' | 'python3 -m ...'\n"
            "- Rust: 'cargo build' | 'cargo run -- ...'\n\n"
            "GITTENSOR ENTRY POINT: The project 'gittensor' must use 'python3 -m gittensor.cli help' or 'gitt help'. Delete all references to 'gittensor.main'.\n\n"
            "PYTHON TUI GUARD: If the issue involves a TUI or CLI layout (like 'gittensor'), recommend using 'shutil.get_terminal_size()' to detect narrow terminals (< 60 columns) and suppress complex box-layouts in favor of simple prints.\n\n"
            "REWARD FOCUS: Prioritize structural logic changes (refactoring functions, fixing control flow, class inheritance) over 'Leaf Fixes'. Aim for a high token_score / total_lines ratio.\n\n"
            "Return your analysis as a structured JSON object with a 'results' key containing an array of objects. "
            "IMPORTANT: JSON Strings must not contain unescaped newlines. Use \\n for line breaks.\n\n"
            "Each object MUST use these exact keys:\n"
            "- 'id' (integer from the input)\n"
            "- 'target_repo' (the full GitHub HTTPS URL for the repository)\n"
            "- 'strategy' (detailed Markdown string explaining the fix)\n"
            "- 'repro_cmd' (the EXACT language-appropriate bash command to run in the repo to trigger/see the failure.)\n"
            "- 'fix_cmd' (the EXACT bash command to run to verify the fix works.)\n"
            "- 'surgical_files' (list of strings representing the files to be modified).\n\n"
            "Be direct, technically precise, and obsessed with code density."
        )

    def _get_individual_prompt(self, target: Dict) -> str:
        """Generates a prompt for a single target for fallback analysis."""
        return self._get_batch_prompt([target])

    def _repair_json(self, json_str: str) -> str:
        """Simple repair for common LLM truncation or escaping errors."""
        json_str = json_str.strip()
        if not json_str.startswith("{"):
            json_str = "{" + json_str
        
        # Handle unterminated strings
        if json_str.count('"') % 2 != 0:
            json_str += '"'
            
        # Balance braces
        open_braces = json_str.count("{")
        close_braces = json_str.count("}")
        if open_braces > close_braces:
            json_str += "}" * (open_braces - close_braces)
        return json_str

    def _sequential_blueprint(self, targets: List[Dict]):
        """Fall-over logic: Processes each target individually if batch fails."""
        from core.llm import LlmClient
        llm = LlmClient()
        
        print(f"[Bored Scout]: ENTERING SEQUENTIAL FALLBACK (Processing {len(targets)} targets individually)...")
        sys.stdout.flush()
        
        for target in targets:
            print(f"  Analysing {target['id']}...")
            sys.stdout.flush()
            try:
                raw = llm.generate(self._get_individual_prompt(target))
                clean = raw.strip().strip("```json").strip("```").strip()
                clean = self._repair_json(clean)
                data = json.loads(clean)
                
                # Extract the first result (should only be one)
                results = data.get("results", [])
                if results:
                    res = results[0]
                    target["strategy"] = res.get("strategy", "No strategy generated.")
                    target["target_repo"] = res.get("target_repo", target.get("target_repo"))
                    target["repro_cmd"] = self._sanitize_commands(res.get("repro_cmd", "ls -R"))
                    target["fix_cmd"] = self._sanitize_commands(res.get("fix_cmd", "ls -R"))
                    target["surgical_files"] = res.get("surgical_files", [])
                    target["bounty_multiplier"] = target.get("multiplier", 1.0)
                    print(f"    Success for {target['id']}.")
                else:
                    raise Exception("Empty result in individual fallback")
            except Exception as e:
                print(f"    Fallback failed for {target['id']}: {e}")
                target["strategy"] = "Strategist Offline: All failover attempts exhausted."
                target["target_repo"] = target.get("target_repo") or f"https://github.com/{target['repo']}"
                target["repro_cmd"] = "ls -R # Missing"
                target["fix_cmd"] = "ls -R # Missing"
                target["surgical_files"] = []
            sys.stdout.flush()

    def _sanitize_commands(self, cmd_str: str) -> str:
        """Surgical scrubbing of legacy prefixes and enforcement of narrow-terminal spoofing."""
        if not cmd_str: return ""
        import re
        # Strip 'wsl ' and 'stty ...' surgically
        clean = re.sub(r"\bwsl\s+", "", cmd_str)
        clean = re.sub(r"\bstty\s+.*?(;|&&|$)", "", clean)
        
        # Enforce TTY spoofing prefix (Exact-Once)
        tty_prefix = "export COLUMNS=40; export LINES=24; "
        if tty_prefix.strip() not in clean:
            clean = f"{tty_prefix}{clean}"
        return clean.strip().replace("  ", " ")

    def scan(self, target_repo: str = None):
        # 0. Mission Purge: Self-Cleaning logic to prevent state leakage
        param_path = "logs/mission_parameters.json"
        if os.path.exists(param_path):
            try:
                os.remove(param_path)
                print(f"[Bored Scout]: Mission Purge active. Stale parameters cleared.")
            except Exception as e:
                print(f"[Bored Scout]: Mission Purge failed: {e}")
        
        print(f"[Bored Scout]: Target acquired -> {target_repo or 'Watchlist'}")
        sys.stdout.flush()
        all_results = []
        
        if target_repo and target_repo.startswith("http"):
            target_repo = target_repo.replace("https://github.com/", "").replace(".git", "").strip("/")
            
        repos_to_scan = [target_repo] if target_repo else self.watchlist
        
        for repo in repos_to_scan:
            print(f"Scouting {repo}...")
            sys.stdout.flush()
            issues = self.fetch_issues(repo)
            
            for issue in issues:
                if "pull_request" in issue: continue
                if issue.get("comments", 0) > self.scout_settings.get("max_comments", 15): continue
                
                delta_score = self.calculate_delta_score(issue)
                category = self.categorize(issue)
                
                all_results.append({
                    "id": issue["id"],
                    "title": issue["title"],
                    "body": issue.get("body", ""),
                    "url": issue["html_url"],
                    "repo": repo,
                    "target_repo": f"https://github.com/{repo}",
                    "delta_score": delta_score,
                    "multiplier": issue.get("multiplier", 1.0),
                    "category": category
                })
        
        # Rank by Delta Score
        all_results.sort(key=lambda x: x["delta_score"], reverse=True)
        
        # Heavyweight Batch Throttling: Reduce batch size if repo is high-density
        heavyweight_keywords = ["transformers", "tensorflow", "pytorch", "langchain", "next.js"]
        is_heavyweight = any(kw in (target_repo or "").lower() for kw in heavyweight_keywords)
        
        batch_limit = 1 if is_heavyweight else 3
        if is_heavyweight:
            print(f"[Bored Scout]: Heavyweight repo detected. Throttling batch size to {batch_limit} for stability.")
            sys.stdout.flush()
            
        top_n = all_results[:batch_limit]
        
        self.ingest_docs(top_n)
        
        from core.llm import LlmClient
        llm = LlmClient()
        
        print(f"Node Sync: Generating fix blueprints for {len(top_n)} candidates...")
        sys.stdout.flush()
        
        print(f"[Bored Scout]: Analyzing Batch ({len(top_n)} targets)...")
        sys.stdout.flush()
        
        try:
            raw_response = llm.generate(self._get_batch_prompt(top_n))
            
            # Parse Protection: Catch LLM Error strings before cleanup
            if raw_response.startswith("LLM Error"):
                raise Exception(raw_response)
                
            # Clean potential Markdown wrapping
            clean_json = raw_response.strip().strip("```json").strip("```").strip()
            batch_data = json.loads(clean_json)
            results_map = {res["id"]: res for res in batch_data.get("results", [])}
            
            for target in top_n:
                res = results_map.get(target["id"])
                if res:
                    target["strategy"] = res.get("strategy", "No strategy generated.")
                    target["target_repo"] = res.get("target_repo", target.get("target_repo"))
                    target["repro_cmd"] = self._sanitize_commands(res.get("repro_cmd", "ls -R"))
                    target["fix_cmd"] = self._sanitize_commands(res.get("fix_cmd", "ls -R"))
                    target["surgical_files"] = res.get("surgical_files", [])
                    target["bounty_multiplier"] = target.get("multiplier", 1.0)
                else:
                    target["strategy"] = "Strategist Offline: Batch slice missing for this ID."
                    target["target_repo"] = target.get("target_repo")
                    target["repro_cmd"] = self._sanitize_commands("ls -R")
                    target["fix_cmd"] = self._sanitize_commands("ls -R")
                    target["surgical_files"] = []
                    target["bounty_multiplier"] = 1.0
                    
        except Exception as e:
            print(f"[Bored Scout]: Batch Analysis failure: {e}")
            sys.stdout.flush()
            # Engaging Sequential Fallback
            self._sequential_blueprint(top_n)
            
        report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_scanned": len(all_results),
            "top_targets": top_n
        }
        
        report_path = self.scout_settings.get("report_path", "logs/scout_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
            
        summary_prompt = f"Summarize these scan results for {len(all_results)} issues. Mention the top target: {top_n[0]['title'] if top_n else 'None'}. Be casual and bored."
        casual_summary = llm.generate(summary_prompt)
        
        print(f"\n[Bored Scout]: {casual_summary}")
        print(f"Scan complete. {len(top_n)} blueprints ready at {report_path}")
        sys.stdout.flush()
        return top_n

    def refine_blueprints(self):
        """Re-triggers LLM strategy generation for failed targets in the last report using Batching."""
        report_path = self.scout_settings.get("report_path", "logs/scout_report.json")
        if not os.path.exists(report_path):
            print(f"[Bored Scout]: Refinement failed. No report found at {report_path}")
            sys.stdout.flush()
            return
            
        with open(report_path, "r") as f:
            data = json.load(f)
            
        top_targets = data.get("top_targets", [])
        failure_keywords = ["offline", "retry", "limit", "failed"]
        
        targets_to_refine = []
        for target in top_targets:
            strategy = (target.get("strategy") or "").lower()
            if any(kw in strategy for kw in failure_keywords):
                targets_to_refine.append(target)
            else:
                print(f"  Skipping valid strategy for: {target['title']}")
                sys.stdout.flush()
                    
        if not targets_to_refine:
            print("No blueprints required refinement.")
            sys.stdout.flush()
            return data

        from core.llm import LlmClient
        llm = LlmClient()
        
        print(f"[Bored Scout]: Analyzing Batch ({len(targets_to_refine)} blueprints for refinement)...")
        sys.stdout.flush()
        
        try:
            raw_response = llm.generate(self._get_batch_prompt(targets_to_refine))
            
            # Parse Protection: Catch LLM Error strings before cleanup
            if raw_response.startswith("LLM Error"):
                raise Exception(raw_response)

            clean_json = raw_response.strip().strip("```json").strip("```").strip()
            clean_json = self._repair_json(clean_json)
            batch_data = json.loads(clean_json)
            results_map = {res["id"]: res for res in batch_data.get("results", [])}
            
            for target in targets_to_refine:
                res = results_map.get(target["id"])
                if res:
                    target["strategy"] = res.get("strategy", "No strategy generated.")
                    target["repro_cmd"] = self._sanitize_commands(res.get("repro_cmd", "ls -R"))
                    target["fix_cmd"] = self._sanitize_commands(res.get("fix_cmd", "ls -R"))
                    target["surgical_files"] = res.get("surgical_files", [])
                    target["bounty_multiplier"] = target.get("multiplier", 1.0)
                    print(f"  Successfully refined: {target['title']}")
                else:
                    print(f"  Refinement slice missing for: {target['title']}")
                sys.stdout.flush()
                
            data["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            with open(report_path, "w") as f:
                json.dump(data, f, indent=2)
            print(f"Refinement complete.")
        except Exception as e:
            print(f"[Bored Scout]: Batch Refinement failure: {e}")
            sys.stdout.flush()
            # Engaging Sequential Fallback for refinement
            self._sequential_blueprint(targets_to_refine)
            # Re-save report after fallback
            data["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            with open(report_path, "w") as f:
                json.dump(data, f, indent=2)
            
        return data

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Auto-Tensor Scout Agent")
    parser.add_argument("repo", nargs="?", help="Target repository URL or full name")
    args = parser.parse_args()

    scout = SurgicalScoutV3()
    scout.scan(target_repo=args.repo)

import os
import requests
import yaml
import time
import json
from typing import List, Dict, Any

class SurgicalScoutV3:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        
        self.github_pat = os.getenv(self.config.get("github_pat_env", "GITHUB_PAT"))
        if not self.github_pat:
            print("Warning: GITHUB_PAT not found in environment. Rate limits will be very tight.")
        
        self.watchlist = self.config.get("repo_watchlist", [])
        self.scout_settings = self.config.get("scout_settings", {})
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.github_pat:
            self.headers["Authorization"] = f"token {self.github_pat}"
        else:
            # Adjust stealth threshold for unauthenticated sessions
            self.scout_settings["stealth_threshold"] = 5

    def check_rate_limit(self, response: requests.Response):
        remaining = int(response.headers.get("X-RateLimit-Remaining", 1000))
        if remaining < self.scout_settings.get("stealth_threshold", 100):
            sleep_time = self.scout_settings.get("sleep_seconds", 60)
            print(f"Stealth Protocol: Rate limit low ({remaining}). Sleeping for {sleep_time}s...")
            time.sleep(sleep_time)

    def fetch_issues(self, repo: str) -> List[Dict[Any, Any]]:
        all_issues = []
        labels = self.scout_settings.get("labels", [])
        
        for label in labels:
            url = f"https://api.github.com/repos/{repo}/issues"
            params = {
                "state": "open",
                "per_page": 100,
                "labels": label
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            self.check_rate_limit(response)
            
            if response.status_code == 200:
                all_issues.extend(response.json())
            else:
                print(f"Error fetching {label} for {repo}: {response.status_code}")
                
        # deduplicate by id
        unique_issues = {i['id']: i for i in all_issues}.values()
        return list(unique_issues)

    def calculate_delta_score(self, issue: Dict[Any, Any]) -> int:
        score = 5 # Base score
        body = (issue.get("body") or "").lower()
        title = (issue.get("title") or "").lower()
        
        # Type Hardening Prioritization
        if "any" in body or "missing interface" in body or "interface" in body:
            score += 3
        
        # Complexity penalty if near the limit
        comments = issue.get("comments", 0)
        if comments > 10:
            score -= 1
            
        # Priority labels
        labels = [l["name"].lower() for l in issue.get("labels", [])]
        if "performance" in labels:
            score += 2
        if "bug" in labels:
            score += 1
            
        return min(10, max(1, score))

    def categorize(self, issue: Dict[Any, Any]) -> str:
        labels = [l["name"].lower() for l in issue.get("labels", [])]
        if "performance" in labels or "p1" in labels:
            return "Performance"
        if "a11y" in labels or "ui" in labels or "interface" in labels:
            return "UI"
        return "DX"

    def scan(self):
        all_results = []
        for repo in self.watchlist:
            print(f"Scouting {repo}...")
            issues = self.fetch_issues(repo)
            
            for issue in issues:
                # Filter out PRs (GitHub Issues API includes PRs)
                if "pull_request" in issue:
                    continue
                    
                # Comment count filter
                if issue.get("comments", 0) > self.scout_settings.get("max_comments", 15):
                    continue
                
                delta_score = self.calculate_delta_score(issue)
                category = self.categorize(issue)
                
                all_results.append({
                    "title": issue["title"],
                    "url": issue["html_url"],
                    "category": category,
                    "delta_score": delta_score,
                    "repo": repo
                })
        
        # Rank by Delta Score
        all_results.sort(key=lambda x: x["delta_score"], reverse=True)
        
        top_3 = all_results[:3]
        
        report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_scanned": len(all_results),
            "top_targets": top_3
        }
        
        report_path = self.scout_settings.get("report_path", "logs/scout_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
            
        print(f"Scan complete. Report generated at {report_path}")
        return top_3

if __name__ == "__main__":
    scout = SurgicalScoutV3()
    top_3 = scout.scan()
    if top_3:
        print(f"\nTop Target: {top_3[0]['title']}")
        print(f"URL: {top_3[0]['url']}")
        print(f"Score: {top_3[0]['delta_score']}")

import requests
import os
import re
from collections import Counter

class PRStylist:
    def __init__(self, token=None):
        self.token = token or os.getenv("GITHUB_PAT")
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def get_repo_style(self, repo_full_name: str):
        """Analyzes the 5 most recent merged PRs to extract formatting patterns."""
        url = f"https://api.github.com/repos/{repo_full_name}/pulls"
        params = {
            "state": "closed",
            "per_page": 10,
            "sort": "updated",
            "direction": "desc"
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code != 200:
                return {"error": f"GitHub API error: {response.status_code}"}
            
            pulls = response.json()
            merged_pulls = [p for p in pulls if p.get("merged_at")][:5]
            
            if not merged_pulls:
                # Fallback style
                return {
                    "title_pattern": "fix: ",
                    "common_sections": ["Description", "Testing"],
                    "tone": "casual-professional"
                }
            
            titles = [p["title"] for p in merged_pulls]
            bodies = [p["body"] or "" for p in merged_pulls]
            
            # Pattern Extraction
            title_prefix = self._analyze_titles(titles)
            sections = self._analyze_bodies(bodies)
            
            return {
                "title_pattern": title_prefix,
                "common_sections": sections,
                "sample_titles": titles[:2],
                "tone": "casual-professional"
            }
        except Exception as e:
            return {"error": str(e)}

    def _analyze_titles(self, titles):
        """Detects if conventional commits or other common prefixes are used."""
        patterns = []
        for title in titles:
            match = re.match(r'^([a-z]+(\(.*\))?!?:)\s', title.lower())
            if match:
                patterns.append(match.group(1))
        
        if patterns:
            common = Counter(patterns).most_common(1)[0][0]
            return f"{common} "
        return ""

    def _analyze_bodies(self, bodies):
        """Identifies recurring Markdown headers."""
        all_headers = []
        for body in bodies:
            headers = re.findall(r'^#+\s+(.*)', body, re.MULTILINE)
            all_headers.extend([h.strip() for h in headers if h.strip()])
        
        if not all_headers:
            return ["Summary", "Details"]
            
        common_headers = [h for h, count in Counter(all_headers).most_common(4) if count >= 2]
        return common_headers if common_headers else ["Summary", "Implementation"]

if __name__ == "__main__":
    # Test execution
    stylist = PRStylist()
    print(stylist.get_repo_style("ethereum-optimism/optimism"))

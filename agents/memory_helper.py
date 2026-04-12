import os
import re
import time
from typing import Dict, Any, Optional

class ReflectionEngine:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.skills_dir = os.path.join(self.base_dir, "skills")
        self.instr_dir = os.path.join(self.base_dir, "instructions")
        
        os.makedirs(self.skills_dir, exist_ok=True)
        os.makedirs(self.instr_dir, exist_ok=True)

    def _get_path(self, name: str, is_skill: bool = True) -> str:
        folder = self.skills_dir if is_skill else self.instr_dir
        prefix = "skills_" if is_skill else "instructions_"
        return os.path.join(folder, f"{prefix}{name}.md")

    def update_skill(self, repo: str, strategy_data: Dict[str, Any], agent: str = "scout"):
        """Deduplication-aware skill update. Replaces existing header or appends."""
        path = self._get_path(agent, is_skill=True)
        if not os.path.exists(path):
            return

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        header = f"## [{repo}]"
        
        # Construct the skill block
        new_block = [
            header,
            f"- **REPO**: {repo}",
            f"- **ENTRY**: {strategy_data.get('entry_point', 'NONE')}",
            f"- **MULTIPLIER**: {strategy_data.get('multiplier', '1.0')}x",
            f"- **LAST_VERIFIED**: {timestamp}",
            f"- **STRATEGY**: {strategy_data.get('strategy', 'Generic Fix')[:200]}"
        ]
        new_block_str = "\n".join(new_block) + "\n"

        # Regex to find and replace existing block
        pattern = re.escape(header) + r"$.*?(?=\n## |$)"
        if re.search(pattern, content, re.MULTILINE | re.DOTALL):
            updated_content = re.sub(pattern, new_block_str.strip(), content, flags=re.MULTILINE | re.DOTALL)
        else:
            updated_content = content.strip() + "\n\n" + new_block_str

        with open(path, "w", encoding="utf-8") as f:
            f.write(updated_content)

    def record_forbidden_pattern(self, error_signal: str, agent: str = "scout"):
        """Negative Reflection: Appends forbidden patterns to instructions."""
        path = self._get_path(agent, is_skill=False)
        if not os.path.exists(path):
            return

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Simple error parsing (e.g. 'stty', 'wsl')
        forbidden_val = "Unknown Error"
        if "stty" in error_signal.lower():
            forbidden_val = "stty injection in non-interactive shell"
        elif "wsl" in error_signal.lower():
            forbidden_val = "wsl prefix on native Linux"
        elif "export" in error_signal.lower() and "failed to spawn" in error_signal.lower():
            forbidden_val = "uv run export (Use bash -c wrapper)"

        entry = f"- FORBIDDEN: {forbidden_val} (Logged: {time.strftime('%Y-%m-%d')})\n"
        
        # Check if already present
        if any(forbidden_val in line for line in lines):
            return

        # Append to the Forbidden Patterns section
        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)

    def get_repo_skill(self, repo: str, agent: str = "scout") -> Optional[Dict[str, str]]:
        """Reads a verified skill if it exists."""
        path = self._get_path(agent, is_skill=True)
        if not os.path.exists(path):
            return None

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        header = f"## [{repo}]"
        if header not in content:
            return None

        # Extract the block
        pattern = re.escape(header) + r"$.*?(?=\n## |$)"
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        if not match:
            return None

        block = match.group(0)
        data = {}
        for line in block.splitlines():
            if "**ENTRY**:" in line:
                data["entry_point"] = line.split(":", 1)[1].strip()
            if "**STRATEGY**:" in line:
                data["strategy"] = line.split(":", 1)[1].strip()
            if "**MULTIPLIER**:" in line:
                data["multiplier"] = line.split(":", 1)[1].strip().replace("x", "")
        
        return data

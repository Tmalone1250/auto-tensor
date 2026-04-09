import os
import json
from core.llm import LlmClient

class SkillWriter:
    def __init__(self, skills_path="SKILLS.md"):
        self.skills_path = skills_path
        self.llm = LlmClient()

    def synthesize_lesson(self, mission_data: dict, build_logs: dict) -> str:
        """Summarizes a successful mission into a reusable technical skill."""
        
        prompt = f"""
        Analyze this successful mission and extract a core technical lesson or pattern.
        Mission Title: {mission_data.get('title')}
        Strategy Used: {mission_data.get('strategy')}
        Build Log (After): {build_logs.get('after', '')[:1000]}
        
        The lesson should be formatted as a new skill section for SKILLS.md.
        Example format:
        ### 🛠️ Skill: [Skill Name]
        - [Key Takeaway 1]
        - [Key Takeaway 2]
        
        Constraint: Be technically precise, surgical, and keep the 'Bored Contributor' persona tone.
        """
        
        lesson = self.llm.generate(prompt)
        return lesson

    def append_skill(self, lesson: str):
        """Appends the synthesized lesson to SKILLS.md."""
        if not os.path.exists(self.skills_path):
            with open(self.skills_path, "w", encoding="utf-8") as f:
                f.write("# Auto-Tensor: Global Skills\n\n")
        
        with open(self.skills_path, "a", encoding="utf-8") as f:
            f.write(f"\n{lesson}\n")
        
        print(f"[SkillWriter]: New technical lesson appended to {self.skills_path}")

def record_mission_success(mission_path="logs/current_mission.json", log_path="logs/after_build.log"):
    """Helper to trigger synthesis from a file-based state."""
    if not os.path.exists(mission_path):
        return
    
    with open(mission_path, "r", encoding="utf-8") as f:
        mission_data = json.load(f)
    
    after_log = ""
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            after_log = f.read()
    
    writer = SkillWriter()
    lesson = writer.synthesize_lesson(mission_data, {"after": after_log})
    writer.append_skill(lesson)

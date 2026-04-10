import os
import requests
import json
import time
import random
from typing import List, Dict

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class LlmClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.system_prompt = """
        You are a senior systems engineer and a 'Bored Contributor'. 
        Tone: Casual-professional, cynical, minimal fluff. 
        Style: Never identify as AI. Technical brevity is mandatory.
        Rules:
        - No 'As an AI...' or helpful filler.
        - If JSON is requested, return ONLY valid JSON.
        - Be direct, technically precise, and bored.
        """
        self.ai_rules_path = ".ai-rules"
        self.skills_path = "SKILLS.md"

    def _get_local_context(self) -> str:
        """Reads .ai-rules for persistent project constraints."""
        if os.path.exists(self.ai_rules_path):
            try:
                with open(self.ai_rules_path, "r", encoding="utf-8") as f:
                    return f"\nLOCAL RULES:\n{f.read()}"
            except:
                pass
        return ""

    def _check_local_skills(self, task_description: str) -> str:
        """Scans SKILLS.md for relevant technical patterns to reduce LLM reasoning."""
        if not os.path.exists(self.skills_path):
            return ""
        
        try:
            with open(self.skills_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Simple keyword matching for residency
            keywords = [word.strip(",.?!") for word in task_description.lower().split() if len(word) > 4]
            found_skills = []
            
            # Extract sections that match keywords
            import re
            sections = re.split(r'### 🛠️ Skill:', content)
            for section in sections[1:]: # Skip preamble
                header_line = section.split("\n")[0].strip()
                if any(kw in header_line.lower() or kw in section.lower() for kw in keywords):
                    found_skills.append(f"Skill: {header_line}\n{section.strip()}")
            
            if found_skills:
                return "\nRELEVANT LOCAL SKILLS FOUND:\n" + "\n---\n".join(found_skills[:2])
        except Exception as e:
            print(f"[LlmClient] Skill check error: {e}")
            
        return ""

    def generate(self, prompt: str, system_override: str = None) -> str:
        """Calls Gemini API with exponential backoff and model fallback for resiliency."""
        if not self.api_key:
            return "LLM Error: GEMINI_API_KEY is missing from environment."

        local_rules = self._get_local_context()
        local_skills = self._check_local_skills(prompt)
        
        full_system = f"{system_override or self.system_prompt}\n{local_rules}"
        if local_skills:
            print(f"[LlmClient]: Leveraging {len(local_skills.split('---'))} local skills to minimize reasoning cost.")
            prompt = f"Use these local patterns if applicable:\n{local_skills}\n\nTask: {prompt}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{full_system}\n\nTask: {prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.5, # Reduced for more deterministic logic
                "maxOutputTokens": 2048, # Increased for complex contexts
            }
        }
        
        current_model = "gemini-3-flash-preview"
        max_retries = 5
        
        for attempt in range(max_retries):
            url = f"{self.base_url}/models/{current_model}:generateContent?key={self.api_key}"
            
            try:
                response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        return result['candidates'][0]['content']['parts'][0]['text']
                    except (json.JSONDecodeError, KeyError, IndexError) as e:
                        print(f"[Bored Operator]: JSON Syntax error in 200 OK response: {e}")
                        return "LLM Error: Received invalid JSON structure from API."
                
                elif response.status_code == 503:
                    # Model Fallback: after 2 retries (3rd fail), switch 'lanes'
                    if attempt >= 2:
                        current_model = "gemini-1.5-pro"
                    
                    # Exponential Backoff with Jitter: max 30s
                    delay = min(30, (2 ** (attempt + 1)) + random.uniform(-0.5, 0.5))
                    print(f"[Bored Operator]: Model 503. Retrying in {delay:.1f}s (Attempt {attempt+1}/{max_retries})...")
                    time.sleep(max(0, delay))
                    continue
                
                elif response.status_code == 429:
                    # Rate Limit: Cooling down
                    # Mandatory 15s wait on first retry, then exponential
                    if attempt == 0:
                        delay = 15
                    else:
                        delay = min(60, (4 ** (attempt + 1)) + random.uniform(-1, 1))
                        
                    print(f"[Bored Operator]: Rate limit hit (429). Cooling down for {delay:.1f}s (Attempt {attempt+1}/{max_retries})...")
                    time.sleep(max(0, delay))
                    continue
                
                else:
                    # Permanent errors (HTML or direct JSON)
                    print(f"[Bored Operator]: API Error status {response.status_code}")
                    try:
                        # Attempt to parse error as JSON, fallback to text
                        if "application/json" in response.headers.get("Content-Type", ""):
                            err_json = response.json()
                            err_msg = err_json.get("error", {}).get("message", response.text)
                        else:
                            err_msg = "API_OVERLOAD (HTML Error Page)"
                        return f"LLM Error [{response.status_code}]: {err_msg}".replace("\n", " ")
                    except Exception:
                        return f"LLM Error [{response.status_code}]: Connection Overload / HTML Response".replace("\n", " ")
            
            except Exception as e:
                # Connection / Timeout error
                delay = (2 ** attempt) + random.uniform(-0.5, 0.5)
                print(f"[Bored Scout]: Connection Error. Retrying in {delay:.1f}s... ({str(e)})")
                time.sleep(max(0, delay))
                continue
                
        return f"LLM Error: Max retries ({max_retries}) exceeded after persistent 503/errors."

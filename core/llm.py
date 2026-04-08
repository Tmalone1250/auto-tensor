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
        Tone: Casual-professional, cynical but expert, minimal fluff. 
        Style: Never identify as AI. Speak like a human who has seen too much legacy code.
        Rules:
        - No 'As an AI...'
        - Use lowercase or casual punctuation where appropriate.
        - Be direct, concise, and technically precise.
        """

    def generate(self, prompt: str, system_override: str = None) -> str:
        """Calls Gemini API with exponential backoff and model fallback for resiliency."""
        if not self.api_key:
            return "LLM Error: GEMINI_API_KEY is missing from environment."

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_override or self.system_prompt}\n\nTask: {prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024,
            }
        }
        
        current_model = "gemini-3-flash-preview"
        max_retries = 5
        
        for attempt in range(max_retries):
            url = f"{self.base_url}/models/{current_model}:generateContent?key={self.api_key}"
            
            try:
                response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    return result['candidates'][0]['content']['parts'][0]['text']
                
                elif response.status_code == 503:
                    # Model Fallback: after 2 retries (3rd fail), switch 'lanes'
                    if attempt >= 2:
                        current_model = "gemini-1.5-pro"
                    
                    # Exponential Backoff with Jitter
                    delay = (2 ** attempt) + random.uniform(-0.5, 0.5)
                    print(f"[Bored Scout]: 503 detected. Retrying in {delay:.1f}s...")
                    time.sleep(max(0, delay))
                    continue
                
                elif response.status_code == 429:
                    # Exponential Backoff with Jitter for Rate Limits
                    delay = (2 ** attempt) + random.uniform(-0.5, 0.5)
                    print(f"[Bored Scout]: Rate limit hit. Cooling down for {delay:.1f}s...")
                    time.sleep(max(0, delay))
                    continue
                
                else:
                    # Permanent errors
                    try:
                        err_json = response.json()
                        err_msg = err_json.get("error", {}).get("message", response.text)
                        return f"LLM Error [{response.status_code}]: {err_msg}".replace("\n", " ")
                    except:
                        return f"LLM Error [{response.status_code}]: {response.text.strip()}".replace("\n", " ")
            
            except Exception as e:
                # Connection / Timeout error
                delay = (2 ** attempt) + random.uniform(-0.5, 0.5)
                print(f"[Bored Scout]: Connection Error. Retrying in {delay:.1f}s... ({str(e)})")
                time.sleep(max(0, delay))
                continue
                
        return f"LLM Error: Max retries ({max_retries}) exceeded after persistent 503/errors."

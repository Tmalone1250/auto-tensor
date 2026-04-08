import os
import requests
import json
from typing import List, Dict
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class LlmClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={self.api_key}"
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
        """Calls Gemini API to generate content with the 'Bored Contributor' persona."""
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
        
        try:
            response = requests.post(self.url, json=payload, headers={"Content-Type": "application/json"})
            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                # Flatten the error and try to extract clear message
                try:
                    err_json = response.json()
                    err_msg = err_json.get("error", {}).get("message", response.text)
                    return f"LLM Error [{response.status_code}]: {err_msg}".replace("\n", " ")
                except:
                    return f"LLM Error [{response.status_code}]: {response.text.strip()}".replace("\n", " ")
        except Exception as e:
            return f"LLM Exception: {str(e)}".replace("\n", " ")

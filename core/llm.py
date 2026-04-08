import os
import requests
from typing import List, Dict

class LlmClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
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
                return f"LLM Error: {response.text}"
        except Exception as e:
            return f"Exception: {str(e)}"

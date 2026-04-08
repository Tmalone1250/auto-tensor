import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = "gemini-3-flash"
api_version = "v1"
url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent?key={api_key}"

payload = {
    "contents": [{"parts": [{"text": "Hello, respond with 'Systems Online' if you can hear me."}]}]
}

try:
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

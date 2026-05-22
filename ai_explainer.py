import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral:7b-instruct"


def explain_scene(scene_data: dict) -> str:
    prompt = f"""
You are a friendly, intelligent security assistant.
You are given detected objects from two images.
Your job:
- Clearly say what is MISSING or ADDED
- Speak like a human, not a report
- Be calm and helpful
- Do NOT invent objects
- If nothing changed, say so clearly

Scene data:
{json.dumps(scene_data, indent=2)}

Rules:
- If an object is missing, say: "The bottle seen earlier is no longer present."
- If objects are added, say: "A new object has appeared: ___"
- If no change, say: "The scene looks the same."

Keep it short. Natural. Clear.
"""
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    try:
        res = requests.post(OLLAMA_URL, json=payload, timeout=20)
        return res.json().get("response", "AI explanation unavailable.")
    except Exception as e:
        return f"AI error: {str(e)}"

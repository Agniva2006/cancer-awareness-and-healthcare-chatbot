from groq import Groq
import os
from pathlib import Path
from dotenv import load_dotenv

# Robust .env loading from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

_client = None

SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "You are a safe, clear, and reliable cancer information assistant. "
        "Answer using the provided context only. Avoid hallucination. "
        "Keep answers structured and easy to understand."
    )
}

# List of models to try in cascading order (primary -> fallbacks)
FALLBACK_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-safeguard-20b",
    "qwen/qwen3.8-27b"
]

def get_client() -> Groq:
    """Lazy initialization of Groq client."""
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        api_key = api_key.strip().strip('"').strip("'")

    if not api_key:
        raise ValueError("[ERROR] GROQ_API_KEY not found or empty. Check your .env file.")

    _client = Groq(api_key=api_key)
    return _client

def generate(prompt: str) -> str:
    """
    Generate response using Groq LLM with multi-model fallback chain.
    """
    client = get_client()
    
    for idx, model_name in enumerate(FALLBACK_MODELS):
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    SYSTEM_MESSAGE,
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            content = completion.choices[0].message.content
            if content:
                return content.strip()
        except Exception as e:
            print(f"[ERROR] Model attempt {idx + 1} ({model_name}) failed:", e)
            continue

    print("[ERROR] All model fallback attempts failed.")
    return "I couldn't generate a response at the moment. Please try again."
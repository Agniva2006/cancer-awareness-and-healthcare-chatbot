from groq import Groq
import os
from pathlib import Path
from dotenv import load_dotenv

# 🔹 Robust .env loading from project root
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


def get_client() -> Groq:
    """
    Lazy initialization of Groq client.
    """
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
    Generate response using Groq LLM with fallback support and strict safety parity.
    """
    try:
        client = get_client()
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                SYSTEM_MESSAGE,
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=300
        )
        return completion.choices[0].message.content.strip()

    except Exception as e:
        print("[ERROR] Groq Primary Error:", e)

        # Fallback model with identical system safety prompt
        try:
            client = get_client()
            completion = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    SYSTEM_MESSAGE,
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=250
            )
            return completion.choices[0].message.content.strip()

        except Exception as fallback_error:
            print("[ERROR] Groq Fallback Error:", fallback_error)
            return "I couldn't generate a response at the moment. Please try again."

from groq import Groq
import os
from dotenv import load_dotenv


# 🔹 Force load .env from project root
load_dotenv(dotenv_path=".env",override=True)


def get_api_key():
    api_key = os.getenv("GROQ_API_KEY")

    if api_key:
        api_key = api_key.strip().strip('"').strip("'")

    if not api_key:
        raise ValueError("❌ GROQ_API_KEY not found or empty. Check your .env file.")

    return api_key


# 🔹 Load key ONCE
api_key = get_api_key()

# 🔹 Debug (safe: partial print only)
print("DEBUG KEY LOADED:", api_key[:6], "...")

# 🔹 Initialize client
client = Groq(api_key=api_key)


def generate(prompt: str) -> str:
    """
    Generate response using Groq LLM
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a safe, clear, and reliable cancer information assistant. "
                        "Answer using the provided context only. Avoid hallucination. "
                        "Keep answers structured and easy to understand."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=250
        )

        return completion.choices[0].message.content.strip()

    except Exception as e:
        print("❌ Groq Primary Error:", e)

        # 🔁 Fallback model
        try:
            completion = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )

            return completion.choices[0].message.content.strip()

        except Exception as fallback_error:
            print("❌ Groq Fallback Error:", fallback_error)
            return "I couldn't generate a response at the moment. Please try again."
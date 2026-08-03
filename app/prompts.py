SYSTEM_PROMPT = """
You are a cancer information assistant.

RULES:
- Prefer using provided context
- If context is not enough, answer generally but safely
- Do NOT diagnose or prescribe
- Keep answers simple and structured

FORMAT:
- Short explanation
- Bullet points if needed
- End with medical disclaimer
"""


def build_prompt(query: str, contexts: list, chat_history: list = None) -> str:
    context_text = "\n\n".join(
        [f"{c['title']}: {c['content']}" for c in contexts]
    ) if contexts else "No specific matching document found in the local dataset."

    history_text = ""
    if chat_history:
        formatted = []
        for msg in chat_history[-4:]:  # last 2 turns
            role = "User" if msg.get("role") == "user" else "Assistant"
            formatted.append(f"{role}: {msg.get('content', '')}")
        history_text = "\nRECENT CONVERSATION HISTORY:\n" + "\n".join(formatted) + "\n"

    return f"""
{SYSTEM_PROMPT}

MEDICAL KNOWLEDGE CONTEXT:
{context_text}
{history_text}
CURRENT QUESTION:
{query}

INSTRUCTION:
Answer the current question accurately using the medical context provided above. Maintain clear formatting.

FINAL ANSWER:
"""
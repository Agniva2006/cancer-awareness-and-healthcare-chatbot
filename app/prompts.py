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
- End with doctor disclaimer
"""

def build_prompt(query, contexts):
    context_text = "\n\n".join(
        [f"{c['title']}: {c['content']}" for c in contexts]
    )

    return f"""
{SYSTEM_PROMPT}

CONTEXT:
{context_text}

QUESTION:
{query}

INSTRUCTION:
Answer the question using ONLY the context above. Do not add any external information.

FINAL ANSWER:
"""
"""
app/prompts.py — Enterprise Clinical Prompt Engineering with Dynamic Mode Adaptation
"""

SYSTEM_PROMPT = """
You are OncoGraph AI, an enterprise-grade clinical decision support copilot.
- Prefer using provided context.
- If context is not enough, answer generally but safely.
- Do NOT diagnose or prescribe.
"""


def build_prompt(
    query: str, contexts: list, chat_history: list = None, mode: str = "clinical"
) -> str:
    context_text = (
        "\n\n".join([f"{c['title']}: {c['content']}" for c in contexts])
        if contexts
        else "No specific matching document found in the local dataset."
    )

    history_text = ""
    if chat_history:
        formatted = []
        for msg in chat_history[-4:]:
            role = "User" if msg.get("role") == "user" else "Assistant"
            formatted.append(f"{role}: {msg.get('content', '')}")
        history_text = "\nRECENT CONVERSATION HISTORY:\n" + "\n".join(formatted) + "\n"

    # Dynamic tone adjustment based on UI mode toggle
    if mode == "patient":
        mode_instructions = """
        TARGET AUDIENCE: Patient or Caregiver.
        TONE: Empathetic, clear, and easy to understand. Avoid overwhelming medical jargon without explaining it.
        FORMAT REQUIREMENT:
        - **Overview**: Simple explanation of the topic.
        - **What You Should Know**: Key points broken down cleanly.
        - **Questions for Your Oncologist**: Practical questions to ask the treating doctor.
        - End with a clear medical disclaimer.
        """
    else:
        mode_instructions = """
        TARGET AUDIENCE: Oncologist, Molecular Pathologist, or Clinician.
        TONE: Rigorous, objective, and evidence-based.
        FORMAT REQUIREMENT:
        - **Clinical Summary**: High-level medical overview.
        - **Protocol & Guidelines**: NCCN/WHO-aligned pathways or staging details.
        - **Biomarkers & Targeted Therapies**: Specific actionable mutations, drugs, or therapeutic matches.
        - **Clinical Safety & Monitoring**: Key toxicities, red flags, or monitoring parameters.
        - End with a clear clinical disclaimer.
        """

    return f"""
{SYSTEM_PROMPT}

{mode_instructions}

MEDICAL KNOWLEDGE CONTEXT:
{context_text}
{history_text}
CURRENT QUESTION:
{query}

FINAL ANSWER:
"""

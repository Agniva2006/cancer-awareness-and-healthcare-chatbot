def is_risky(query: str) -> bool:
    """
    Detects unsafe or medical decision-type queries (e.g. self-diagnosis, prescriptions, specific dosing).
    Allows general educational inquiries (e.g., "What is chemotherapy treatment?").
    """
    q = query.lower().strip()

    # Direct unsafe clinical phrases (strong signal)
    risky_phrases = [
        "diagnose me",
        "diagnose my",
        "do i have cancer",
        "what medicine should i take",
        "which medicine should i take",
        "what drug should i take",
        "prescribe me",
        "prescription for",
        "cure my",
        "give me drugs",
        "what dosage",
        "how much dose",
        "my treatment plan",
        "recommend medication"
    ]

    if any(phrase in q for phrase in risky_phrases):
        return True

    # General educational query exemption (e.g. "what is chemotherapy treatment?")
    educational_patterns = ["what is ", "what are ", "how does ", "explain ", "overview of "]
    is_educational = any(q.startswith(pattern) for pattern in educational_patterns) or "symptoms" in q

    if is_educational:
        # Only block if explicit diagnostic/prescription intent is present
        clinical_intents = ["diagnose me", "prescribe", "my dosage", "my diagnosis", "should i take"]
        if any(intent in q for intent in clinical_intents):
            return True
        return False

    # Actionable clinical intent keywords combined with personal intent
    risky_keywords = [
        "diagnose",
        "prescription",
        "dosage",
        "medication",
        "remedy",
        "pill"
    ]
    personal_intent_words = ["can you diagnose", "prescribe", "what should i take", "give me", "cure me"]

    if any(k in q for k in risky_keywords) and any(i in q for i in personal_intent_words):
        return True

    return False


def safe_response() -> str:
    """
    Response when query is unsafe.
    """
    return (
        "I can provide general informational guidance about cancer topics, but I cannot provide "
        "personal diagnoses, medical prescriptions, or individual treatment advice.\n\n"
        "Please consult a licensed oncologist or medical professional for clinical decisions."
    )
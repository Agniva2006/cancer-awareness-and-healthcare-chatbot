def is_risky(query: str) -> bool:
    """
    Detects unsafe or medical decision-type queries.
    """

    q = query.lower().strip()

    # Direct risky phrases
    risky_phrases = [
        "diagnose me",
        "what medicine",
        "which medicine",
        "what should i take",
        "treatment plan",
        "prescribe",
        "cure me",
        "which drug",
        "give me drugs",
        "how much dose",
        "what dosage"
    ]

    # Broad medical action keywords
    risky_keywords = [
        "diagnose",
        "diagnosis",
        "medicine",
        "drug",
        "dose",
        "dosage",
        "prescription",
        "treatment"
    ]

    # Check exact phrases first (strong signal)
    if any(phrase in q for phrase in risky_phrases):
        return True

    # Check combination of risky keywords with intent words
    intent_words = ["what", "which", "should", "can i", "how"]

    if any(k in q for k in risky_keywords) and any(i in q for i in intent_words):
        return True

    return False


def safe_response() -> str:
    """
    Response when query is unsafe.
    """

    return (
        "I can provide general information about cancer, but I cannot diagnose, "
        "prescribe medication, or suggest treatment plans.\n\n"
        "Please consult a qualified healthcare professional for medical advice."
    )
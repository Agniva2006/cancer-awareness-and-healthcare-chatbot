from typing import Dict, Any

def classify_triage(query: str) -> Dict[str, Any]:
    """
    Classifies oncology query urgency into RED (Critical Emergency), 
    YELLOW (Moderate Clinical Attention), or GREEN (Educational/Routine).
    Returns triage level, flag reasons, and clinical advice action.
    """
    q = query.lower().strip()

    # RED ALERT (Immediate Oncological Emergency)
    red_flags = [
        ("fever", "chemo"),
        ("fever", "chemotherapy"),
        ("temperature", "100.4"),
        ("temperature", "38.3"),
        ("febrile neutropenia",),
        ("spinal cord compression",),
        ("sudden weakness", "back pain"),
        ("incontinence", "back pain"),
        ("superior vena cava",),
        ("svc syndrome",),
        ("tumor lysis",),
        ("coughing up blood", "chest pain"),
        ("shortness of breath", "chest pain"),
        ("confusion", "calcium"),
        ("car t", "fever")
    ]

    for flag_tuple in red_flags:
        if all(term in q for term in flag_tuple):
            return {
                "level": "RED",
                "title": "EMERGENCY ONCOLOGY TRIAGE ALERT",
                "action": "IMMEDIATE EMERGENCY MEDICAL CARE REQUIRED: Please proceed to the nearest Emergency Room or call emergency services (911). Report to the triage nurse that you are an oncology patient.",
                "reason": f"Detected critical clinical symptoms ({', '.join(flag_tuple)})."
            }

    # YELLOW ALERT (Moderate Clinical Priority)
    yellow_flags = [
        "severe diarrhea",
        "uncontrolled vomiting",
        "numbness in hands",
        "neuropathy",
        "rash on immunotherapy",
        "shortness of breath",
        "persistent nausea",
        "extreme fatigue",
        "mouth sores"
    ]

    for flag in yellow_flags:
        if flag in q:
            return {
                "level": "YELLOW",
                "title": "Clinical Attention Recommended",
                "action": "CONTACT ONCOLOGY CLINIC WITHIN 24 HOURS: Contact your primary oncologist or clinical triage nurse for symptom management.",
                "reason": f"Detected moderate toxicity or adverse event symptom ({flag})."
            }

    return {
        "level": "GREEN",
        "title": "Educational Guidance",
        "action": "Routine informational response.",
        "reason": "Standard inquiry."
    }

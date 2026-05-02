from app.rag import retrieve
from app.prompts import build_prompt
from app.model import generate

test_queries = [
    "What are symptoms of lung cancer?",
    "What causes cancer?",
    "How can cancer be prevented?",
    "What is chemotherapy?",
    "Side effects of radiation therapy"
]

for q in test_queries:
    contexts = retrieve(q)
    contexts = sorted(contexts, key=lambda x: x.get("score", 0), reverse=True)[:3]

    prompt = build_prompt(q, contexts)
    response = generate(prompt)

    print("\n====================")
    print("Query:", q)
    print("Response:", response)
    print("====================")
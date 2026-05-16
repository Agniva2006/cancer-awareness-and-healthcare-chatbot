from fastapi import FastAPI
from pydantic import BaseModel
import time
import logging

from app.rag import retrieve
from app.prompts import build_prompt
from app.model import generate
from app.safety import is_risky, safe_response

from fastapi.middleware.cors import CORSMiddleware

# 🔹 Setup logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# 🔹 Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


# 🔹 Request schema
class QueryRequest(BaseModel):
    query: str


@app.get("/")
def home():
    return {"message": "Cancer AI Assistant is running"}


@app.post("/ask")
def ask(request: QueryRequest):
    start_time = time.time()
    query = request.query.strip()

    try:
        # 🔒 Safety check
        if is_risky(query):
            return {
                "query": query,
                "answer": safe_response(),
                "sources": [],
                "confidence": 0.0,
                "latency": 0.0,
                "disclaimer": "For informational purposes only. Consult a doctor."
            }

        # 🔍 Retrieve context
        contexts = retrieve(query)

        # ⚠️ No context found
        if not contexts:
            return {
                "query": query,
                "answer": "I don't have enough information to answer this question.",
                "sources": [],
                "confidence": 0.0,
                "latency": 0.0,
                "disclaimer": "For informational purposes only. Consult a doctor."
            }

        # 🎯 Re-rank (top 3)
        contexts = sorted(contexts, key=lambda x: x.get("score", 0), reverse=True)[:3]

        # 🧠 Build prompt
        prompt = build_prompt(query, contexts)

        # 🤖 Generate response
        response = generate(prompt).strip()

        # 🧹 Smarter source filtering
        query_words = query.lower().split()
        sources = [
            c["title"] for c in contexts
            if any(word in c["title"].lower() for word in query_words)
        ]

        # fallback if filtering removes everything
        if not sources:
            sources = [c["title"] for c in contexts]

        sources = list(set(sources))

        # 📊 Confidence
        confidence = round(contexts[0].get("score", 0), 3)

        # ⏱️ Latency
        latency = round(time.time() - start_time, 3)

        # 📊 Logging
        logging.info(f"Query: {query}")
        logging.info(f"Sources: {sources}")
        logging.info(f"Confidence: {confidence}")
        logging.info(f"Latency: {latency}s")

        return {
            "query": query,
            "answer": response,
            "sources": sources,
            "confidence": confidence,
            "latency": latency,
            "disclaimer": "For informational purposes only. Consult a doctor."
        }

    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return {
            "query": query,
            "answer": "Something went wrong. Please try again.",
            "sources": [],
            "confidence": 0.0,
            "latency": 0.0,
            "disclaimer": "For informational purposes only. Consult a doctor."
        }
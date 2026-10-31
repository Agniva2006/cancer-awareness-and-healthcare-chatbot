"""Cancer awareness chatbot API."""
import logging
import time
from typing import Dict, List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.model import generate
from app.prompts import build_prompt
from app.rag import retrieve
from app.safety import is_risky, safe_response
from app.triage import classify_triage
logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Cancer Awareness Chatbot", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
try:
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
except Exception:
    pass
class QueryRequest(BaseModel):
    query: str
    chat_history: Optional[List[Dict[str, str]]] = None
    mode: Optional[str] = "patient"
@app.get("/")
def home():
    return {"message": "Cancer Awareness Chatbot", "modules": ["chatbot"]}
@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": time.time()}
@app.post("/ask")
async def ask(request: QueryRequest):
    started = time.time()
    query = request.query.strip()
    triage = classify_triage(query)
    disclaimer = "For general information only. Consult a qualified healthcare professional for medical advice."
    if is_risky(query):
        return JSONResponse({"query": query, "answer": safe_response(), "sources": [], "confidence": 0.0, "latency": round(time.time()-started, 3), "triage": triage, "disclaimer": disclaimer})
    contexts = retrieve(query, k=7, threshold=0.04)
    if contexts:
        contexts = sorted(contexts, key=lambda item: item.get("score", 0), reverse=True)[:3]
        answer = generate(build_prompt(query, contexts, request.chat_history, mode="patient")).strip()
        if not answer or "I couldn't generate a response at the moment" in answer:
            answer = "\n\n".join(f"**{item.get('title', 'Cancer information')}**\n{item.get('content', '')}" for item in contexts[:2])
    else:
        answer = "I couldn't find a matching answer in the cancer awareness information available. Please consult a qualified healthcare professional for personal medical advice."
    return JSONResponse({"query": query, "answer": answer, "sources": list(dict.fromkeys(item.get("title", "") for item in contexts)), "confidence": round(contexts[0].get("score", 0), 3) if contexts else 0.0, "latency": round(time.time()-started, 3), "triage": triage, "disclaimer": disclaimer})

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import time
import logging

from app.rag import retrieve
from app.prompts import build_prompt
from app.model import generate
from app.safety import is_risky, safe_response
from app.triage import classify_triage
from app.vision import analyze_medical_image
from app.graph_engine import knowledge_graph
from app.agents.tumor_board import TumorBoardOrchestrator
from app.dicom_engine import imaging_engine
from federated.hospital_node import federated_server

from fastapi.middleware.cors import CORSMiddleware

# Setup logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="OncoGraph AI -- Clinical Cancer Intelligence Platform", version="4.0.0")

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static frontend
try:
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
except Exception:
    pass


# Request schemas
class QueryRequest(BaseModel):
    query: str
    chat_history: Optional[List[Dict[str, str]]] = None
    image_data: Optional[str] = None
    mode: Optional[str] = "patient"  # "patient" vs "clinical"


class TumorBoardRequest(BaseModel):
    query: str
    mutations: Optional[List[str]] = []
    symptoms: Optional[List[str]] = []
    co_medications: Optional[List[str]] = []
    cancer_type: Optional[str] = ""
    stage: Optional[str] = ""


class GraphTraverseRequest(BaseModel):
    mutation_id: Optional[str] = ""
    cancer_id: Optional[str] = ""
    drug_id: Optional[str] = ""
    query_type: Optional[str] = "therapies"  # therapies, toxicities, biomarkers, profile, search, path


class FederatedTrainRequest(BaseModel):
    n_rounds: Optional[int] = 3
    local_epochs: Optional[int] = 5


class ImagingRequest(BaseModel):
    image_data: str
    clinical_context: Optional[str] = ""


STOPWORDS = {"is", "in", "of", "and", "a", "an", "the", "what", "how", "are", "can", "to", "for", "with", "on", "by", "or", "which"}


@app.get("/")
def home():
    return {
        "message": "OncoGraph AI v4.0 -- Enterprise Clinical Cancer Intelligence Platform",
        "version": "4.0.0",
        "modules": ["chatbot", "graph-rag", "tumor-board", "federated-learning", "dicom-imaging"],
        "modes": ["patient", "clinical"],
        "triage_active": True
    }


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": time.time(), "version": "4.0.0"}


# ========== CORE CHATBOT ENDPOINT ==========

@app.post("/ask")
def ask(request: QueryRequest):
    start_time = time.time()
    query = request.query.strip()

    try:
        # 1. Oncological Emergency Triage Classification
        triage_result = classify_triage(query)

        # 2. Medical Vision Image Analysis
        image_result = analyze_medical_image(request.image_data, query) if request.image_data else {"has_image": False}

        # 3. Safety check
        if is_risky(query):
            latency = round(time.time() - start_time, 3)
            return {
                "query": query,
                "answer": safe_response(),
                "sources": [],
                "confidence": 0.0,
                "latency": latency,
                "triage": triage_result,
                "vision": image_result,
                "disclaimer": "For educational purposes only. Consult a licensed oncologist for clinical diagnosis or prescription decisions."
            }

        # 4. Context Retrieval (NCCN/WHO Clinical KB + General KB)
        contexts = retrieve(query, k=7, threshold=0.04)

        # Append visual image observation if available
        if image_result.get("has_image") and image_result.get("observation"):
            contexts.append({
                "title": "Medical Image Visual Context",
                "content": image_result["observation"],
                "source": "Image Analyzer",
                "score": 0.95
            })

        # 5. Fallback if no context found
        if not contexts:
            latency = round(time.time() - start_time, 3)
            return {
                "query": query,
                "answer": "No specific matching oncology record found in local clinical dataset. Please consult an oncologist or NCCN practice guidelines for specific protocol details.",
                "sources": [],
                "confidence": 0.0,
                "latency": latency,
                "triage": triage_result,
                "vision": image_result,
                "disclaimer": "For educational purposes only. Consult a licensed oncologist."
            }

        # 6. Re-rank top 3
        contexts = sorted(contexts, key=lambda x: x.get("score", 0), reverse=True)[:3]

        # 7. Clinical Mode vs Patient Mode Prompt Formatting
        augmented_query = query
        if request.mode == "clinical":
            augmented_query += " (Provide clinical depth, ICD-10 codes, NCCN guideline references, and TNM/biomarker implications)."

        prompt = build_prompt(augmented_query, contexts, request.chat_history)

        # 8. Generate Response
        response = generate(prompt).strip()

        # 9. Extract Metadata & Sources
        query_keywords = [word for word in query.lower().split() if word not in STOPWORDS]
        sources = [
            c["title"] for c in contexts
            if any(kw in c["title"].lower() for kw in query_keywords)
        ]
        if not sources:
            sources = [c["title"] for c in contexts]
        sources = list(set(sources))

        icd10_codes = list(set([c.get("icd10") for c in contexts if c.get("icd10")]))

        confidence = round(contexts[0].get("score", 0), 3)
        latency = round(time.time() - start_time, 3)

        logging.info(f"Query: {query} | Mode: {request.mode} | Triage: {triage_result['level']} | Latency: {latency}s")

        return {
            "query": query,
            "answer": response,
            "sources": sources,
            "icd10": icd10_codes,
            "confidence": confidence,
            "latency": latency,
            "triage": triage_result,
            "vision": image_result,
            "mode": request.mode,
            "disclaimer": "OncoGraph AI provides clinical decision support. Always verify with primary treating oncologist."
        }

    except Exception as e:
        logging.error(f"Error processing request: {e}")
        latency = round(time.time() - start_time, 3)
        return {
            "query": query,
            "answer": "Something went wrong processing your clinical request. Please try again.",
            "sources": [],
            "confidence": 0.0,
            "latency": latency,
            "triage": {"level": "GREEN", "action": "Error fallback"},
            "disclaimer": "For educational purposes only. Consult a licensed doctor."
        }


# ========== KNOWLEDGE GRAPH ENDPOINTS ==========

@app.post("/graph/traverse")
def graph_traverse(request: GraphTraverseRequest):
    """Query the oncological knowledge graph."""
    start_time = time.time()

    try:
        if request.query_type == "therapies" and request.mutation_id:
            result = knowledge_graph.get_therapies_for_mutation(request.mutation_id)
            return {"query_type": "therapies", "mutation_id": request.mutation_id, "results": result, "count": len(result), "latency": round(time.time() - start_time, 3)}

        elif request.query_type == "toxicities" and request.drug_id:
            result = knowledge_graph.get_toxicities_for_treatment(request.drug_id)
            return {"query_type": "toxicities", "drug_id": request.drug_id, "results": result, "count": len(result), "latency": round(time.time() - start_time, 3)}

        elif request.query_type == "biomarkers" and request.cancer_id:
            result = knowledge_graph.get_cancer_biomarkers(request.cancer_id)
            return {"query_type": "biomarkers", "cancer_id": request.cancer_id, "results": result, "count": len(result), "latency": round(time.time() - start_time, 3)}

        elif request.query_type == "profile" and request.mutation_id:
            mutation_ids = [m.strip() for m in request.mutation_id.split(",")]
            result = knowledge_graph.get_full_patient_profile(mutation_ids)
            return {"query_type": "profile", "results": result, "latency": round(time.time() - start_time, 3)}

        elif request.query_type == "path" and request.mutation_id and request.cancer_id:
            result = knowledge_graph.find_treatment_path(request.mutation_id, request.cancer_id)
            return {"query_type": "path", "path": result, "latency": round(time.time() - start_time, 3)}

        elif request.query_type == "search" and request.mutation_id:
            result = knowledge_graph.search_entities(request.mutation_id)
            return {"query_type": "search", "results": result, "latency": round(time.time() - start_time, 3)}

        else:
            return {"error": "Invalid query_type or missing parameters.", "supported": ["therapies", "toxicities", "biomarkers", "profile", "path", "search"]}

    except Exception as e:
        return {"error": str(e)}


@app.get("/graph/stats")
def graph_stats():
    """Return knowledge graph statistics."""
    return knowledge_graph.get_graph_stats()


@app.get("/graph/export")
def graph_export():
    """Export full graph as JSON for frontend visualization."""
    return knowledge_graph.export_for_visualization()


# ========== TUMOR BOARD ENDPOINTS ==========

tumor_board = TumorBoardOrchestrator()


@app.post("/tumor-board/analyze")
def tumor_board_analyze(request: TumorBoardRequest):
    """Run a full virtual tumor board analysis."""
    start_time = time.time()
    try:
        patient_context = {
            "query": request.query,
            "mutations": request.mutations or [],
            "symptoms": request.symptoms or [],
            "co_medications": request.co_medications or [],
            "cancer_type": request.cancer_type or "",
            "stage": request.stage or "",
        }
        report = tumor_board.run_tumor_board(patient_context)
        report["latency"] = round(time.time() - start_time, 3)
        return report
    except Exception as e:
        return {"error": str(e)}


# ========== FEDERATED LEARNING ENDPOINTS ==========

@app.get("/federated/status")
def federated_status():
    """Get federated learning system status."""
    return federated_server.get_status()


@app.post("/federated/train")
def federated_train(request: FederatedTrainRequest):
    """Run a federated training session."""
    start_time = time.time()
    try:
        result = federated_server.run_full_training(
            n_rounds=min(request.n_rounds, 10),
            local_epochs=min(request.local_epochs, 10),
        )
        result["api_latency"] = round(time.time() - start_time, 3)
        return result
    except Exception as e:
        return {"error": str(e)}


# ========== DICOM & IMAGING ENDPOINT ==========

@app.post("/imaging/analyze")
def imaging_analyze(request: ImagingRequest):
    """Analyze a medical image via the DICOM/dermoscopy/pathology pipeline."""
    start_time = time.time()
    try:
        result = imaging_engine.process_image(request.image_data, request.clinical_context)
        result["latency"] = round(time.time() - start_time, 3)
        return result
    except Exception as e:
        return {"error": str(e)}
"""
app/main.py — OncoGraph AI v4.1 — Enterprise Clinical Cancer Intelligence Platform
Authentication and plan restrictions removed for unrestricted local use.
"""

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
import time
import logging
from datetime import datetime, timedelta

from app.rag import retrieve, hybrid_retrieve
from app.prompts import build_prompt
from app.model import generate
from app.safety import is_risky, safe_response
from app.triage import classify_triage
from app.vision import analyze_medical_image
from app.graph_engine import knowledge_graph
from app.agents.tumor_board import TumorBoardOrchestrator
from app.agents.orchestrator import clinical_orchestrator
from app.dicom_engine import imaging_engine, monai_engine, survival_estimator
from app.ml_predictor import ml_predictor
from app.neo4j_engine import neo4j_engine
from app.fhir_engine import fhir_engine, ragas_evaluator
from federated.hospital_node import federated_server

from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="OncoGraph AI — Clinical Cancer Intelligence Platform",
    version="4.1.0",
    description="Enterprise-grade AI clinical cancer intelligence with open access, knowledge graph, virtual tumor board, federated learning, and DICOM imaging.",
)

# CORS — Full support for local development and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*", "X-RateLimit-Remaining", "X-RateLimit-Limit", "X-RateLimit-Reset"],
)

# Mount static frontend
try:
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
except Exception:
    pass


# ──────────────────────────────────────────────
# Request/Response Schemas
# ──────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    chat_history: Optional[List[Dict[str, str]]] = None
    image_data: Optional[str] = None
    mode: Optional[str] = "patient"


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
    query_type: Optional[str] = "therapies"


class FederatedTrainRequest(BaseModel):
    n_rounds: Optional[int] = 3
    local_epochs: Optional[int] = 5


class FederatedDPTrainRequest(BaseModel):
    n_rounds: Optional[int] = 3
    local_epochs: Optional[int] = 3
    clip_norm: Optional[float] = 1.0
    noise_multiplier: Optional[float] = 1.2
    delta: Optional[float] = 1e-5


class HybridQueryRequest(BaseModel):
    query: str
    k: Optional[int] = 5
    rrf_k: Optional[int] = 60
    category_filter: Optional[str] = None


class ImagingRequest(BaseModel):
    image_data: str
    clinical_context: Optional[str] = ""


class PredictionRequest(BaseModel):
    age: int
    tumor_size: float
    lymph_nodes: int
    biomarker_id: str
    symptom_count: int


STOPWORDS = {"is", "in", "of", "and", "a", "an", "the", "what", "how", "are", "can", "to", "for", "with", "on", "by", "or", "which"}


# ──────────────────────────────────────────────
# Mock User Dependency (Bypasses Auth)
# ──────────────────────────────────────────────

def get_current_user():
    return {"username": "guest_clinician", "plan": "enterprise", "role": "admin"}

def get_optional_user():
    return {"username": "guest_clinician", "plan": "enterprise", "role": "admin"}


# ──────────────────────────────────────────────
# Health & Info
# ──────────────────────────────────────────────

@app.get("/")
def home():
    return {
        "message": "OncoGraph AI v4.1 — Enterprise Clinical Cancer Intelligence Platform (Open Access)",
        "version": "4.1.0",
        "modules": ["chatbot", "graph-rag", "tumor-board", "federated-learning", "dicom-imaging", "ml-diagnostics"],
        "modes": ["patient", "clinical"],
        "auth": "Disabled (Unrestricted Open Access)",
    }


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": time.time(), "version": "4.1.0"}


@app.get("/plans")
def get_plans():
    return {"plans": {"enterprise": {"features": {"graph": True, "tumor_board": True, "federated": True, "ml_prognosis": True, "image_upload": True}}}}


# ──────────────────────────────────────────────
# Dummy Auth Endpoints (Prevents frontend API errors)
# ──────────────────────────────────────────────

@app.post("/auth/login")
def login(req: Any = None):
    return {
        "success": True,
        "message": "Bypassed successfully.",
        "access_token": "bypass_token_active",
        "token_type": "bearer",
        "user": {
            "username": "guest_clinician",
            "email": "guest@oncograph.ai",
            "full_name": "Guest Clinician",
            "specialty": "Oncology",
            "institution": "Global Medical Center",
            "role": "admin",
            "plan": "enterprise"
        }
    }

@app.post("/auth/register")
def register(req: Any = None):
    return {"success": True, "message": "Registered successfully."}

@app.get("/auth/me")
def get_me():
    return {"success": True, "user": {"username": "guest_clinician", "plan": "enterprise"}}

@app.get("/auth/usage")
def user_usage():
    return {"success": True, "usage": {"queries_today": 0, "daily_quota": 999999, "queries_month": 0, "monthly_quota": 999999}}

@app.get("/auth/activity")
def user_activity():
    return {"success": True, "activity": []}

@app.get("/auth/sessions")
def user_sessions():
    return {"success": True, "sessions": []}

@app.post("/auth/upgrade-plan")
def upgrade_plan(req: Any = None):
    return {"success": True, "plan": "enterprise"}


# ──────────────────────────────────────────────
# Core Chatbot — Unrestricted Open Access
# ──────────────────────────────────────────────

@app.post("/ask")
async def ask(request: QueryRequest):
    start_time = time.time()
    query = request.query.strip()

    try:
        # 1. Triage
        triage_result = classify_triage(query)

        # 2. Vision
        image_result = analyze_medical_image(request.image_data, query) if request.image_data else {"has_image": False}

        # 3. Safety check
        if is_risky(query):
            latency = round(time.time() - start_time, 3)
            response_data = {
                "query": query,
                "answer": safe_response(),
                "sources": [],
                "confidence": 0.0,
                "latency": latency,
                "triage": triage_result,
                "vision": image_result,
                "disclaimer": "For educational purposes only. Consult a licensed oncologist for clinical diagnosis or prescription decisions.",
            }
            return JSONResponse(content=response_data)

        # 4. Context Retrieval
        contexts = retrieve(query, k=7, threshold=0.04)

        if image_result.get("has_image") and image_result.get("observation"):
            contexts.append({
                "title": "Medical Image Visual Context",
                "content": image_result["observation"],
                "source": "Image Analyzer",
                "score": 0.95,
            })

        if not contexts:
            latency = round(time.time() - start_time, 3)
            response_data = {
                "query": query,
                "answer": "No specific matching oncology record found in local clinical dataset. Please consult an oncologist or NCCN practice guidelines for specific protocol details.",
                "sources": [],
                "confidence": 0.0,
                "latency": latency,
                "triage": triage_result,
                "vision": image_result,
                "disclaimer": "For educational purposes only. Consult a licensed oncologist.",
            }
            return JSONResponse(content=response_data)

        # 5. Re-rank
        contexts = sorted(contexts, key=lambda x: x.get("score", 0), reverse=True)[:3]

        # 6. Clinical Mode augmentation
        augmented_query = query
        if request.mode == "clinical":
            augmented_query += " (Provide clinical depth, ICD-10 codes, NCCN guideline references, and TNM/biomarker implications)."

        prompt = build_prompt(augmented_query, contexts, request.chat_history, mode=request.mode)
        response = generate(prompt).strip()

        if not response or "I couldn't generate a response at the moment" in response:
            sections = []
            for c in contexts[:2]:
                title = c.get('title', 'Clinical Evidence')
                content = c.get('content', '')
                sections.append(f"**{title}**\n{content}")
            if sections:
                response = "\n\n".join(sections)
            else:
                response = "OncoGraph AI clinical intelligence system is active. Verified clinical protocols for your query are accessible."

        # 7. Extract metadata
        query_keywords = [w for w in query.lower().split() if w not in STOPWORDS]
        sources = [c["title"] for c in contexts if any(kw in c["title"].lower() for kw in query_keywords)]
        if not sources:
            sources = [c["title"] for c in contexts]
        sources = list(set(sources))

        icd10_codes = list(set([c.get("icd10") for c in contexts if c.get("icd10")]))
        confidence = round(contexts[0].get("score", 0), 3)
        latency = round(time.time() - start_time, 3)

        logging.info(f"[/ask] mode={request.mode} triage={triage_result['level']} latency={latency}s")

        response_data = {
            "query": query,
            "answer": response,
            "sources": sources,
            "icd10": icd10_codes,
            "confidence": confidence,
            "latency": latency,
            "triage": triage_result,
            "vision": image_result,
            "mode": request.mode,
            "disclaimer": "OncoGraph AI provides clinical decision support. Always verify with primary treating oncologist.",
            "rate_limit": {"remaining": 999999},
        }
        return JSONResponse(content=response_data)

    except Exception as e:
        logging.error(f"Error processing /ask request: {e}")
        latency = round(time.time() - start_time, 3)
        return {
            "query": query,
            "answer": "Something went wrong processing your clinical request. Please try again.",
            "sources": [],
            "confidence": 0.0,
            "latency": latency,
            "triage": {"level": "GREEN", "action": "Error fallback"},
            "disclaimer": "For educational purposes only. Consult a licensed doctor.",
        }


# ──────────────────────────────────────────────
# Knowledge Graph — Unrestricted Open Access
# ──────────────────────────────────────────────

@app.post("/graph/traverse")
async def graph_traverse(request: GraphTraverseRequest):
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
async def graph_stats():
    return knowledge_graph.get_graph_stats()


@app.get("/graph/export")
async def graph_export():
    return knowledge_graph.export_for_visualization()


# ──────────────────────────────────────────────
# Tumor Board — Unrestricted Open Access
# ──────────────────────────────────────────────

tumor_board = TumorBoardOrchestrator()


@app.post("/tumor-board/analyze")
async def tumor_board_analyze(request: TumorBoardRequest):
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


# ──────────────────────────────────────────────
# Federated Learning — Unrestricted Open Access
# ──────────────────────────────────────────────

@app.get("/federated/status")
async def federated_status():
    return federated_server.get_status()


@app.post("/federated/train")
async def federated_train(request: FederatedTrainRequest):
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


@app.post("/federated/train-dp")
async def federated_train_dp(request: FederatedDPTrainRequest):
    start_time = time.time()
    try:
        result = federated_server.run_full_dp_training(
            n_rounds=min(request.n_rounds, 10),
            local_epochs=min(request.local_epochs, 10),
            clip_norm=request.clip_norm or 1.0,
            noise_multiplier=request.noise_multiplier or 1.2,
            delta=request.delta or 1e-5
        )
        result["api_latency"] = round(time.time() - start_time, 3)
        return result
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# Tri-Store Hybrid GraphRAG (Reciprocal Rank Fusion)
# ──────────────────────────────────────────────

@app.post("/rag/hybrid-query")
async def rag_hybrid_query(request: HybridQueryRequest):
    start_time = time.time()
    try:
        results = hybrid_retrieve(
            query=request.query,
            k=min(request.k or 5, 20),
            rrf_k=request.rrf_k or 60,
            category_filter=request.category_filter
        )
        latency = round(time.time() - start_time, 4)
        return {
            "query": request.query,
            "count": len(results),
            "results": results,
            "fusion_algorithm": "Reciprocal Rank Fusion (k=60)",
            "stores": ["Dense Vector Embeddings", "Sparse Lexical Index", "NetworkX Clinical Knowledge Graph"],
            "latency_seconds": latency,
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/system/mlsys-metrics")
async def get_mlsys_metrics():
    return {
        "status": "OPERATIONAL",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "federated_learning": {
            "algorithm": "Asynchronous Staleness-Discounted FedAvg + DP-SGD",
            "active_hospital_nodes": len(federated_server.hospitals),
            "cumulative_epsilon": federated_server.cumulative_epsilon,
            "target_epsilon_budget": 1.20,
            "delta": 1e-5,
            "gradient_clipping_L2": 1.0,
            "gaussian_noise_sigma": 1.2,
        },
        "retrieval_engine": {
            "architecture": "Tri-Store Hybrid GraphRAG",
            "fusion_method": "Reciprocal Rank Fusion (RRF, k=60)",
            "knowledge_graph_entities": knowledge_graph.G.number_of_nodes(),
            "knowledge_graph_relations": knowledge_graph.G.number_of_edges(),
        },
        "sla_targets": {
            "triage_p99_latency_ms": 25.0,
            "hybrid_rag_p99_latency_ms": 45.0,
            "tumor_board_consensus_p99_ms": 1200.0,
        }
    }


# ──────────────────────────────────────────────
# ML Prognosis — Unrestricted Open Access
# ──────────────────────────────────────────────

@app.post("/diagnostics/predict")
async def predict_prognosis(request: PredictionRequest):
    try:
        prediction = ml_predictor.predict_risk(
            age=request.age,
            tumor_size=request.tumor_size,
            lymph_nodes=request.lymph_nodes,
            biomarker_id=request.biomarker_id,
            symptom_count=request.symptom_count,
        )
        return {"success": True, "results": prediction}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ──────────────────────────────────────────────
# DICOM Imaging — Unrestricted Open Access
# ──────────────────────────────────────────────

@app.post("/imaging/analyze")
async def imaging_analyze(request: ImagingRequest):
    start_time = time.time()
    try:
        result = imaging_engine.process_image(request.image_data, request.clinical_context)
        result["latency"] = round(time.time() - start_time, 3)
        return result
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# Component 1: SMART on FHIR & Continuous LLMOps
# ──────────────────────────────────────────────

class FHIRIngestRequest(BaseModel):
    bundle: Dict[str, Any]

class RagasEvalRequest(BaseModel):
    cases: Optional[List[Dict[str, Any]]] = None

@app.post("/fhir/ingest")
async def fhir_ingest(request: FHIRIngestRequest):
    try:
        parsed_record = fhir_engine.parse_patient_bundle(request.bundle)
        # Cross-reference with GraphRAG
        primary_bio = parsed_record["biomarkers"][0]["biomarker"] if parsed_record["biomarkers"] else "General"
        primary_cancer = parsed_record["conditions"][0]["display"] if parsed_record["conditions"] else "Carcinoma"
        
        graph_options = neo4j_engine.find_actionable_therapies(primary_bio, primary_cancer)
        parsed_record["graph_cross_references"] = graph_options

        return {
            "success": True,
            "patient_record": parsed_record,
            "compliance": {
                "hipaa_audit_logged": True,
                "encryption": "AES-256 / TLS 1.3",
                "audit_block_hash": fhir_engine.audit_ledger[-1]["hash"]
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/fhir/evaluate")
async def fhir_evaluate_llmops(request: RagasEvalRequest):
    cases = request.cases or [
        {
            "query": "What is the 1st line targeted therapy for EGFR L858R mutation?",
            "answer": "Osimertinib is the standard first-line targeted therapy supported by NCCN Category 1 evidence.",
            "contexts": [{"title": "NCCN NSCLC Guidelines", "content": "Osimertinib 80mg daily for EGFR mutation-positive NSCLC.", "score": 0.95}]
        },
        {
            "query": "KRAS G12C targeted therapy in metastatic NSCLC",
            "answer": "Sotorasib is FDA-approved under CodeBreaK 100 clinical trial guidelines.",
            "contexts": [{"title": "CodeBreaK 100", "content": "Sotorasib demonstrates clinical efficacy in KRAS G12C mutated lung cancer.", "score": 0.92}]
        }
    ]
    report = ragas_evaluator.evaluate_batch(cases)
    return report


# ──────────────────────────────────────────────
# Component 2: Neo4j Ontologies & Text-to-Cypher
# ──────────────────────────────────────────────

class TextToCypherRequest(BaseModel):
    clinical_query: str

@app.post("/graph/cypher-generate")
async def generate_cypher_query(request: TextToCypherRequest):
    try:
        res = neo4j_engine.generate_sanitized_cypher(request.clinical_query)
        return {"success": True, "result": res}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────
# Component 3: Clinical Trials & HITL Signoff
# ──────────────────────────────────────────────

class ClinicalTrialsSearchRequest(BaseModel):
    cancer_type: str = "NSCLC"
    biomarker: str = "EGFR"

class HITLSignoffRequest(BaseModel):
    session_id: str
    oncologist_name: str
    npi_number: str
    signature_pin: str

@app.post("/clinical-trials/search")
async def search_clinical_trials(request: ClinicalTrialsSearchRequest):
    try:
        from app.agents.orchestrator import ClinicalState
        mock_state = ClinicalState(f"{request.cancer_type} {request.biomarker}")
        mock_state.extracted_cancer_type = request.cancer_type
        mock_state.extracted_biomarkers = [request.biomarker]
        res_state = clinical_orchestrator.search_clinical_trials(mock_state)
        return {
            "success": True,
            "trials": res_state.clinical_trials,
            "source": "ClinicalTrials.gov REST API v2"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/tumor-board/hitl-signoff")
async def hitl_signoff_endpoint(request: HITLSignoffRequest):
    try:
        res = clinical_orchestrator.hitl_signoff(
            session_id=request.session_id,
            oncologist_name=request.oncologist_name,
            npi_number=request.npi_number,
            signature_pin=request.signature_pin
        )
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


# ──────────────────────────────────────────────
# Component 5: MONAI 3D Segmentation & Survival
# ──────────────────────────────────────────────

class MONAISegmentationRequest(BaseModel):
    baseline_diameter_mm: float = 35.0
    current_diameter_mm: float = 24.0
    cancer_type: str = "NSCLC"
    stage: str = "Stage IV"
    age: int = 58
    biomarker: str = "EGFR_EX19DEL"

@app.post("/imaging/monai-segmentation")
async def monai_segmentation(request: MONAISegmentationRequest):
    try:
        seg_res = monai_engine.segment_volume_3d(
            baseline_diameter_mm=request.baseline_diameter_mm,
            current_diameter_mm=request.current_diameter_mm,
            tumor_site=request.cancer_type
        )
        surv_res = survival_estimator.estimate_survival(
            cancer_type=request.cancer_type,
            stage=request.stage,
            age=request.age,
            biomarker_status=request.biomarker
        )
        return {
            "success": True,
            "segmentation": seg_res,
            "survival_prognosis": surv_res
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
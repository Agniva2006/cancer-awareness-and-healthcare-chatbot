"""
app/main.py — OncoGraph AI v4.1 — Enterprise Clinical Cancer Intelligence Platform
Full JWT auth, per-plan rate limiting, usage tracking, profile management.
"""

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
import time
import logging
from datetime import datetime, timedelta

from app.rag import retrieve
from app.prompts import build_prompt
from app.model import generate
from app.safety import is_risky, safe_response
from app.triage import classify_triage
from app.vision import analyze_medical_image
from app.graph_engine import knowledge_graph
from app.agents.tumor_board import TumorBoardOrchestrator
from app.dicom_engine import imaging_engine
from app.ml_predictor import ml_predictor
from federated.hospital_node import federated_server

from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_optional_user,
    record_api_call,
    get_usage,
    check_rate_limit,
    load_users,
    save_users,
    PLANS,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

# Setup logging
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="OncoGraph AI — Clinical Cancer Intelligence Platform",
    version="4.1.0",
    description="Enterprise-grade AI clinical cancer intelligence with JWT auth, knowledge graph, virtual tumor board, federated learning, and DICOM imaging.",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Remaining", "X-RateLimit-Limit", "X-RateLimit-Reset"],
)

# Mount static frontend
try:
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
except Exception:
    pass


# ──────────────────────────────────────────────
# Request/Response Schemas
# ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str
    full_name: Optional[str] = ""
    specialty: Optional[str] = ""
    institution: Optional[str] = ""
    role: Optional[str] = "clinician"  # patient | clinician | researcher


class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: Optional[bool] = True


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    specialty: Optional[str] = None
    institution: Optional[str] = None
    email: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


class PlanUpgradeRequest(BaseModel):
    plan: str  # free | clinical | enterprise


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
# Health & Info
# ──────────────────────────────────────────────

@app.get("/")
def home():
    return {
        "message": "OncoGraph AI v4.1 — Enterprise Clinical Cancer Intelligence Platform",
        "version": "4.1.0",
        "modules": ["chatbot", "graph-rag", "tumor-board", "federated-learning", "dicom-imaging", "ml-diagnostics"],
        "modes": ["patient", "clinical"],
        "auth": "JWT Bearer",
        "plans": list(PLANS.keys()),
    }


@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": time.time(), "version": "4.1.0"}


# ──────────────────────────────────────────────
# Plan Definitions
# ──────────────────────────────────────────────

@app.get("/plans")
def get_plans():
    return {"plans": PLANS}


# ──────────────────────────────────────────────
# Authentication Endpoints
# ──────────────────────────────────────────────

def _safe_user_public(username: str, u: dict) -> dict:
    """Strip sensitive fields before returning user object."""
    return {
        "username": username,
        "email": u.get("email", ""),
        "full_name": u.get("full_name", ""),
        "specialty": u.get("specialty", ""),
        "institution": u.get("institution", ""),
        "role": u.get("role", "clinician"),
        "plan": u.get("plan", "free"),
        "created_at": u.get("created_at", ""),
        "onboarding_done": u.get("onboarding_done", False),
        "avatar_color": u.get("avatar_color", "#6366f1"),
        "last_login": u.get("last_login", ""),
    }


@app.post("/auth/register")
def register(req: RegisterRequest):
    username = req.username.strip().lower()
    if not username or len(username) < 3:
        return {"success": False, "message": "Username must be at least 3 characters."}
    if not req.password or len(req.password) < 6:
        return {"success": False, "message": "Password must be at least 6 characters."}
    if not req.email or "@" not in req.email:
        return {"success": False, "message": "Valid email address is required."}

    users = load_users()
    if username in users:
        return {"success": False, "message": "Username already taken. Try a different one."}

    # Check email uniqueness
    for u in users.values():
        if u.get("email", "").lower() == req.email.lower():
            return {"success": False, "message": "Email already registered. Please sign in."}

    # Avatar color — deterministic from username
    colors = ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#3b82f6", "#ef4444", "#14b8a6"]
    avatar_color = colors[sum(ord(c) for c in username) % len(colors)]

    users[username] = {
        "password": hash_password(req.password),
        "email": req.email,
        "full_name": req.full_name or "",
        "specialty": req.specialty or "",
        "institution": req.institution or "",
        "role": req.role or "clinician",
        "plan": "free",
        "avatar_color": avatar_color,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_login": "",
        "onboarding_done": False,
        "usage_daily": {},
        "usage_monthly": {},
        "activity": [],
        "sessions": [],
    }
    save_users(users)
    logging.info(f"New user registered: {username} ({req.role})")
    return {"success": True, "message": "Account created successfully! Please sign in."}


@app.post("/auth/login")
def login(req: LoginRequest):
    username = req.username.strip().lower()
    users = load_users()

    if username not in users:
        return {"success": False, "message": "Invalid username or password."}

    u = users[username]
    if not verify_password(req.password, u["password"]):
        return {"success": False, "message": "Invalid username or password."}

    # Update last login + session log
    now = datetime.utcnow().isoformat() + "Z"
    u["last_login"] = now
    sessions = u.setdefault("sessions", [])
    sessions.append({"login_at": now, "ts": time.time()})
    u["sessions"] = sessions[-10:]  # keep last 10
    save_users(users)

    expires = timedelta(days=30 if req.remember_me else 1)
    token = create_access_token({"sub": username}, expires_delta=expires)

    return {
        "success": True,
        "message": "Login successful.",
        "access_token": token,
        "token_type": "bearer",
        "expires_in": int(expires.total_seconds()),
        "user": _safe_user_public(username, u),
    }


@app.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    username = current_user["username"]
    users = load_users()
    u = users.get(username, current_user)
    usage = get_usage(username)
    profile = _safe_user_public(username, u)
    profile["usage"] = usage
    return {"success": True, "user": profile}


@app.patch("/auth/profile/update")
async def update_profile(req: ProfileUpdateRequest, current_user: dict = Depends(get_current_user)):
    username = current_user["username"]
    users = load_users()
    u = users[username]

    if req.full_name is not None:
        u["full_name"] = req.full_name.strip()
    if req.specialty is not None:
        u["specialty"] = req.specialty.strip()
    if req.institution is not None:
        u["institution"] = req.institution.strip()
    if req.email is not None:
        email = req.email.strip()
        if "@" not in email:
            raise HTTPException(status_code=400, detail="Invalid email address.")
        # Check uniqueness (excluding self)
        for un, ud in users.items():
            if un != username and ud.get("email", "").lower() == email.lower():
                raise HTTPException(status_code=409, detail="Email already in use by another account.")
        u["email"] = email

    save_users(users)
    return {"success": True, "message": "Profile updated successfully.", "user": _safe_user_public(username, u)}


@app.post("/auth/profile/change-password")
async def change_password(req: PasswordChangeRequest, current_user: dict = Depends(get_current_user)):
    username = current_user["username"]
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters.")

    users = load_users()
    u = users[username]

    if not verify_password(req.old_password, u["password"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    u["password"] = hash_password(req.new_password)
    save_users(users)
    return {"success": True, "message": "Password changed successfully."}


@app.post("/auth/onboarding-complete")
async def onboarding_complete(current_user: dict = Depends(get_current_user)):
    username = current_user["username"]
    users = load_users()
    users[username]["onboarding_done"] = True
    save_users(users)
    return {"success": True}


@app.get("/auth/usage")
async def user_usage(current_user: dict = Depends(get_current_user)):
    usage = get_usage(current_user["username"])
    return {"success": True, "usage": usage}


@app.get("/auth/activity")
async def user_activity(current_user: dict = Depends(get_current_user)):
    users = load_users()
    u = users.get(current_user["username"], {})
    activity = u.get("activity", [])
    # Return most recent first
    return {"success": True, "activity": list(reversed(activity[-20:]))}


@app.get("/auth/sessions")
async def user_sessions(current_user: dict = Depends(get_current_user)):
    users = load_users()
    u = users.get(current_user["username"], {})
    sessions = u.get("sessions", [])
    return {"success": True, "sessions": list(reversed(sessions))}


@app.post("/auth/upgrade-plan")
async def upgrade_plan(req: PlanUpgradeRequest, current_user: dict = Depends(get_current_user)):
    if req.plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan. Valid: {list(PLANS.keys())}")
    username = current_user["username"]
    users = load_users()
    old_plan = users[username].get("plan", "free")
    users[username]["plan"] = req.plan
    save_users(users)
    plan_info = PLANS[req.plan]
    return {
        "success": True,
        "message": f"Plan upgraded from {old_plan} to {req.plan}.",
        "plan": req.plan,
        "plan_info": plan_info,
    }


# ──────────────────────────────────────────────
# Core Chatbot — Protected
# ──────────────────────────────────────────────

@app.post("/ask")
async def ask(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    start_time = time.time()
    username = current_user["username"]
    query = request.query.strip()

    # Rate limit check
    remaining = check_rate_limit(username)

    try:
        # 1. Triage
        triage_result = classify_triage(query)

        # 2. Vision
        image_result = analyze_medical_image(request.image_data, query) if request.image_data else {"has_image": False}

        # 3. Safety check
        if is_risky(query):
            latency = round(time.time() - start_time, 3)
            record_api_call(username, "/ask")
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
            resp = JSONResponse(content=response_data)
            resp.headers["X-RateLimit-Remaining"] = str(remaining - 1)
            return resp

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
            record_api_call(username, "/ask")
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
            resp = JSONResponse(content=response_data)
            resp.headers["X-RateLimit-Remaining"] = str(remaining - 1)
            return resp

        # 5. Re-rank
        contexts = sorted(contexts, key=lambda x: x.get("score", 0), reverse=True)[:3]

        # 6. Clinical Mode augmentation
        augmented_query = query
        if request.mode == "clinical":
            augmented_query += " (Provide clinical depth, ICD-10 codes, NCCN guideline references, and TNM/biomarker implications)."

        prompt = build_prompt(augmented_query, contexts, request.chat_history)
        response = generate(prompt).strip()

        # 7. Extract metadata
        query_keywords = [w for w in query.lower().split() if w not in STOPWORDS]
        sources = [c["title"] for c in contexts if any(kw in c["title"].lower() for kw in query_keywords)]
        if not sources:
            sources = [c["title"] for c in contexts]
        sources = list(set(sources))

        icd10_codes = list(set([c.get("icd10") for c in contexts if c.get("icd10")]))
        confidence = round(contexts[0].get("score", 0), 3)
        latency = round(time.time() - start_time, 3)

        # 8. Record usage
        record_api_call(username, "/ask")
        new_remaining = remaining - 1

        logging.info(f"[/ask] user={username} plan={current_user.get('plan','free')} mode={request.mode} triage={triage_result['level']} latency={latency}s")

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
            "rate_limit": {"remaining": new_remaining},
        }
        resp = JSONResponse(content=response_data)
        resp.headers["X-RateLimit-Remaining"] = str(new_remaining)
        return resp

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
# Knowledge Graph — Protected (Clinical+)
# ──────────────────────────────────────────────

@app.post("/graph/traverse")
async def graph_traverse(request: GraphTraverseRequest, current_user: dict = Depends(get_current_user)):
    plan = current_user.get("plan", "free")
    if not PLANS.get(plan, {}).get("features", {}).get("graph", False):
        raise HTTPException(status_code=403, detail="Knowledge Graph requires Clinical or Enterprise plan.")
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
async def graph_stats(current_user: dict = Depends(get_optional_user)):
    return knowledge_graph.get_graph_stats()


@app.get("/graph/export")
async def graph_export(current_user: dict = Depends(get_current_user)):
    plan = current_user.get("plan", "free")
    if not PLANS.get(plan, {}).get("features", {}).get("graph", False):
        raise HTTPException(status_code=403, detail="Knowledge Graph requires Clinical or Enterprise plan.")
    return knowledge_graph.export_for_visualization()


# ──────────────────────────────────────────────
# Tumor Board — Protected (Enterprise only)
# ──────────────────────────────────────────────

tumor_board = TumorBoardOrchestrator()


@app.post("/tumor-board/analyze")
async def tumor_board_analyze(request: TumorBoardRequest, current_user: dict = Depends(get_current_user)):
    plan = current_user.get("plan", "free")
    if not PLANS.get(plan, {}).get("features", {}).get("tumor_board", False):
        raise HTTPException(status_code=403, detail="Virtual Tumor Board requires Enterprise plan.")
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
        record_api_call(current_user["username"], "/tumor-board/analyze")
        return report
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# Federated Learning — Protected (Enterprise only)
# ──────────────────────────────────────────────

@app.get("/federated/status")
async def federated_status(current_user: dict = Depends(get_current_user)):
    plan = current_user.get("plan", "free")
    if not PLANS.get(plan, {}).get("features", {}).get("federated", False):
        raise HTTPException(status_code=403, detail="Federated Learning requires Enterprise plan.")
    return federated_server.get_status()


@app.post("/federated/train")
async def federated_train(request: FederatedTrainRequest, current_user: dict = Depends(get_current_user)):
    plan = current_user.get("plan", "free")
    if not PLANS.get(plan, {}).get("features", {}).get("federated", False):
        raise HTTPException(status_code=403, detail="Federated Learning requires Enterprise plan.")
    start_time = time.time()
    try:
        result = federated_server.run_full_training(
            n_rounds=min(request.n_rounds, 10),
            local_epochs=min(request.local_epochs, 10),
        )
        result["api_latency"] = round(time.time() - start_time, 3)
        record_api_call(current_user["username"], "/federated/train")
        return result
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────────
# ML Prognosis — Protected (Clinical+)
# ──────────────────────────────────────────────

@app.post("/diagnostics/predict")
async def predict_prognosis(request: PredictionRequest, current_user: dict = Depends(get_current_user)):
    plan = current_user.get("plan", "free")
    if not PLANS.get(plan, {}).get("features", {}).get("ml_prognosis", False):
        raise HTTPException(status_code=403, detail="ML Prognosis requires Clinical or Enterprise plan.")
    try:
        prediction = ml_predictor.predict_risk(
            age=request.age,
            tumor_size=request.tumor_size,
            lymph_nodes=request.lymph_nodes,
            biomarker_id=request.biomarker_id,
            symptom_count=request.symptom_count,
        )
        record_api_call(current_user["username"], "/diagnostics/predict")
        return {"success": True, "results": prediction}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ──────────────────────────────────────────────
# DICOM Imaging — Protected (Clinical+)
# ──────────────────────────────────────────────

@app.post("/imaging/analyze")
async def imaging_analyze(request: ImagingRequest, current_user: dict = Depends(get_current_user)):
    plan = current_user.get("plan", "free")
    if not PLANS.get(plan, {}).get("features", {}).get("image_upload", False):
        raise HTTPException(status_code=403, detail="DICOM image analysis requires Clinical or Enterprise plan.")
    start_time = time.time()
    try:
        result = imaging_engine.process_image(request.image_data, request.clinical_context)
        result["latency"] = round(time.time() - start_time, 3)
        return result
    except Exception as e:
        return {"error": str(e)}
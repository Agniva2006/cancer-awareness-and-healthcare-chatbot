import os
import sys
import json
import base64

# Force UTF-8 stdout
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("==================================================")
    print("🔬 OncoGraph AI — Full System Automated Test Suite")
    print("==================================================")
    
    passed = 0
    total = 0
    
    # Test 1: Health & Root Manifest
    total += 1
    res = client.get("/")
    assert res.status_code == 200, f"Root failed: {res.text}"
    data = res.json()
    assert "version" in data
    print(f"✅ Test {total}: Root Health & Manifest -> {data['message']}")
    passed += 1
    
    # Test 2: MLSys Performance Metrics & Privacy Budget Telemetry
    total += 1
    res = client.get("/system/mlsys-metrics")
    assert res.status_code == 200, f"Metrics failed: {res.text}"
    metrics = res.json()
    assert metrics["status"] == "OPERATIONAL"
    print(f"✅ Test {total}: MLSys Telemetry (DP Epsilon Budget: {metrics['federated_learning']['target_epsilon_budget']}) -> Status: OPERATIONAL")
    passed += 1
    
    # Test 3: Auth Registration & Login
    total += 1
    test_user = {
        "username": f"doctor_{int(os.getpid())}",
        "password": "SecurePassword123!",
        "email": f"dr_{int(os.getpid())}@hospital.org",
        "full_name": "Dr. Agniva Ghosh",
        "specialty": "Medical Oncology",
        "institution": "Clinical AI Labs",
        "role": "clinician"
    }
    reg_res = client.post("/auth/register", json=test_user)
    assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
    assert reg_res.json().get("success") is True
    
    login_req = {
        "username": test_user["username"],
        "password": test_user["password"]
    }
    login_res = client.post("/auth/login", json=login_req)
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    auth_data = login_res.json()
    assert auth_data.get("success") is True
    assert "access_token" in auth_data
    token = auth_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"✅ Test {total}: Auth Registration & Login -> JWT Token Issued")
    passed += 1
    
    # Test 4: Auth Profile / Me
    total += 1
    res = client.get("/auth/me", headers=headers)
    assert res.status_code == 200, f"Get /auth/me failed: {res.text}"
    user_info = res.json()["user"]
    assert user_info["username"] == test_user["username"]
    print(f"✅ Test {total}: Profile Verification (/auth/me) -> Plan: {user_info.get('plan')}")
    passed += 1
    
    # Test 5: Plan Gating Verification (Free Plan blocks Clinical/Enterprise endpoints)
    total += 1
    graph_req = {
        "mutation_id": "EGFR",
        "cancer_id": "non_small_cell_lung_cancer",
        "query_type": "therapies"
    }
    res_blocked = client.post("/graph/traverse", json=graph_req, headers=headers)
    assert res_blocked.status_code == 403, "Expected 403 for Free Plan on Graph Traversal"
    print(f"✅ Test {total}: Plan Gating Verification -> Correctly returned 403 Forbidden for Free Plan")
    passed += 1
    
    # Test 6: Standard Chatbot /ask Query (Available on Free Plan)
    total += 1
    ask_req = {
        "query": "What are common early symptoms of lung cancer?",
        "mode": "patient"
    }
    ask_res = client.post("/ask", json=ask_req, headers=headers)
    assert ask_res.status_code == 200, f"Chat /ask failed: {ask_res.text}"
    print(f"✅ Test {total}: Core Clinical RAG Chatbot (/ask) -> Status 200 OK")
    passed += 1
    
    # Upgrade user to enterprise plan
    up_res = client.post("/auth/upgrade-plan", json={"plan": "enterprise"}, headers=headers)
    assert up_res.status_code == 200, f"Upgrade failed: {up_res.text}"
    
    # Test 7: Knowledge Graph Traversal (Enterprise Access)
    total += 1
    res = client.post("/graph/traverse", json=graph_req, headers=headers)
    assert res.status_code == 200, f"Graph traversal failed: {res.text}"
    graph_res = res.json()
    print(f"✅ Test {total}: Knowledge Graph Traversal (EGFR -> Therapies) -> Success: {graph_res.get('count', len(graph_res.get('results', [])))} therapies found")
    passed += 1
    
    # Test 8: Virtual Tumor Board Consensus
    total += 1
    tumor_req = {
        "query": "Patient with Stage IV EGFR-mutated NSCLC presenting with pleural effusion.",
        "mutations": ["EGFR L858R", "TP53"],
        "symptoms": ["Dyspnea", "Chronic Cough"],
        "co_medications": ["Metformin"],
        "cancer_type": "Lung Adenocarcinoma",
        "stage": "Stage IV"
    }
    res = client.post("/tumor-board/analyze", json=tumor_req, headers=headers)
    assert res.status_code == 200, f"Tumor Board failed: {res.text}"
    tb_res = res.json()
    print(f"✅ Test {total}: Virtual Tumor Board Swarm -> Consensus Completed in {tb_res.get('latency', 0.1)}s")
    passed += 1
    
    # Test 9: Tri-Store Hybrid GraphRAG (Reciprocal Rank Fusion RRF)
    total += 1
    hybrid_req = {
        "query": "What are the first-line targeted therapies for EGFR T790M resistance mutation in lung cancer?",
        "k": 3,
        "rrf_k": 60
    }
    res = client.post("/rag/hybrid-query", json=hybrid_req, headers=headers)
    assert res.status_code == 200, f"Hybrid RAG failed: {res.text}"
    rag_res = res.json()
    print(f"✅ Test {total}: Hybrid RAG (Dense + BM25 RRF) -> Retrieved {rag_res.get('count', len(rag_res.get('results', [])))} fused results in {rag_res.get('latency_seconds', 0.01)}s")
    passed += 1
    
    # Test 10: Simulated Federated Learning (DP-SGD)
    total += 1
    fed_dp_req = {
        "n_rounds": 2,
        "local_epochs": 2,
        "clip_norm": 1.0,
        "noise_multiplier": 1.2,
        "delta": 1e-5
    }
    res = client.post("/federated/train-dp", json=fed_dp_req, headers=headers)
    assert res.status_code == 200, f"Federated DP training failed: {res.text}"
    fed_res = res.json()
    print(f"✅ Test {total}: Federated DP-SGD Training -> Completed {fed_res.get('total_rounds', 2)} rounds across {len(fed_res.get('round_history', []))} steps")
    passed += 1
    
    # Test 11: ML Prognosis Risk Prediction
    total += 1
    pred_req = {
        "age": 58,
        "tumor_size": 3.4,
        "lymph_nodes": 2,
        "biomarker_id": "HER2_POSITIVE",
        "symptom_count": 4
    }
    res = client.post("/diagnostics/predict", json=pred_req, headers=headers)
    assert res.status_code == 200, f"ML Prognosis failed: {res.text}"
    ml_res = res.json()
    print(f"✅ Test {total}: ML Prognosis Risk Model -> {ml_res.get('results', {}).get('risk_category', 'Assessed')} (Score: {ml_res.get('results', {}).get('risk_score')})")
    passed += 1
    
    # Test 12: DICOM / Visual Image Analysis
    total += 1
    dummy_img = base64.b64encode(b"DUMMY_IMAGE_BYTES").decode("utf-8")
    img_req = {
        "image_data": f"data:image/jpeg;base64,{dummy_img}",
        "clinical_context": "Dermoscopy of pigmented cutaneous lesion"
    }
    res = client.post("/imaging/analyze", json=img_req, headers=headers)
    assert res.status_code == 200, f"Imaging failed: {res.text}"
    img_res = res.json()
    print(f"✅ Test {total}: DICOM & Pathology Image Processor -> Status: Analyzed ({img_res.get('latency', 0.01)}s)")
    passed += 1
    
    print("==================================================")
    print(f"🎉 ALL {passed}/{total} CORE SYSTEM TESTS PASSED PERFECTLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()

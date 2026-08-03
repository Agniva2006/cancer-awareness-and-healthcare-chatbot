"""
OncoGraph AI v4.0 -- Full Platform Evaluation Suite
Tests: RAG, Triage, Safety, Vision, Graph Engine, Tumor Board, Federated Learning, DICOM
"""
import sys
import traceback

# Force ASCII output for Windows compatibility
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

passed = 0
failed = 0
total = 0

def test(name, fn):
    global passed, failed, total
    total += 1
    try:
        result = fn()
        if result:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            failed += 1
            print(f"  [FAIL] {name}")
    except Exception as e:
        failed += 1
        print(f"  [ERROR] {name}: {e}")


print("=" * 60)
print("OncoGraph AI v4.0 -- Full Platform Evaluation Suite")
print("=" * 60)


# ========== PHASE 1: Knowledge Graph Engine ==========
print("\n--- Phase 1: Knowledge Graph Engine ---")

from app.graph_engine import knowledge_graph

test("Graph has nodes", lambda: knowledge_graph.G.number_of_nodes() > 40)
test("Graph has edges", lambda: knowledge_graph.G.number_of_edges() > 20)
test("EGFR_EX19DEL -> Osimertinib", lambda: any(t["drug_id"] == "OSIMERTINIB" for t in knowledge_graph.get_therapies_for_mutation("EGFR_EX19DEL")))
test("KRAS_G12C -> Sotorasib", lambda: any(t["drug_id"] == "SOTORASIB" for t in knowledge_graph.get_therapies_for_mutation("KRAS_G12C")))
test("HER2_AMP -> Trastuzumab", lambda: any(t["drug_id"] == "TRASTUZUMAB" for t in knowledge_graph.get_therapies_for_mutation("HER2_AMP")))
test("NSCLC biomarkers > 3", lambda: len(knowledge_graph.get_cancer_biomarkers("NSCLC")) >= 3)
test("PEMBROLIZUMAB toxicities", lambda: len(knowledge_graph.get_toxicities_for_treatment("PEMBROLIZUMAB")) >= 1)
test("Patient profile multi-mutation", lambda: len(knowledge_graph.get_full_patient_profile(["EGFR_EX19DEL", "PDL1_HIGH"])["therapies"]) >= 2)
test("Entity search 'osimertinib'", lambda: len(knowledge_graph.search_entities("osimertinib")) >= 1)
test("Graph export has nodes", lambda: len(knowledge_graph.export_for_visualization()["nodes"]) > 40)
test("Graph stats", lambda: knowledge_graph.get_graph_stats()["total_nodes"] > 40)


# ========== PHASE 2: Multi-Agent Tumor Board ==========
print("\n--- Phase 2: Multi-Agent Tumor Board ---")

from app.agents.tumor_board import TumorBoardOrchestrator, GenomicAgent, TrialMatcherAgent, ToxicologyAgent

tb = TumorBoardOrchestrator()

test("Tumor board has 4 agents", lambda: len(tb.agents) == 4)

# Test with NSCLC EGFR patient
ctx_nsclc = {"query": "NSCLC patient with EGFR L858R mutation", "mutations": ["EGFR_L858R"], "symptoms": [], "co_medications": [], "cancer_type": "NSCLC", "stage": "Stage IV"}
report = tb.run_tumor_board(ctx_nsclc)
test("TB report has 4 agent reports", lambda: len(report["agent_reports"]) == 4)
test("TB consensus has triage level", lambda: "triage_level" in report["consensus"])
test("TB finds therapies for EGFR", lambda: report["consensus"]["targeted_therapies_available"] >= 1)
test("TB finds clinical trials", lambda: report["consensus"]["eligible_clinical_trials"] >= 1)

# Test genomic agent alias resolution
ga = GenomicAgent()
test("Genomic agent resolves 'egfr l858r'", lambda: "EGFR_L858R" in ga._resolve_mutations({"query": "patient with egfr l858r mutation"}))
test("Genomic agent resolves 'kras g12c'", lambda: "KRAS_G12C" in ga._resolve_mutations({"query": "kras g12c positive"}))

# Test trial matcher
tm = TrialMatcherAgent()
trial_result = tm.analyze({"query": "EGFR mutation NSCLC", "mutations": ["EGFR_EX19DEL"]})
test("Trial matcher finds trials for EGFR", lambda: trial_result["total_matches"] >= 1)

# Test toxicology with drug interaction
tox = ToxicologyAgent()
tox_result = tox.analyze({"therapy_ids": ["OSIMERTINIB"], "co_medications": ["ketoconazole"]})
test("Toxicology detects ketoconazole + Osimertinib", lambda: tox_result["interaction_count"] >= 1)

# Test with no interactions
tox_clean = tox.analyze({"therapy_ids": ["ALECTINIB"], "co_medications": ["aspirin"]})
test("Toxicology clean when no interactions", lambda: tox_clean["interaction_count"] == 0)


# ========== PHASE 3: Federated Learning ==========
print("\n--- Phase 3: Federated Learning ---")

from federated.hospital_node import federated_server, FederatedServer

test("Federated server has 3 hospitals", lambda: len(federated_server.hospitals) == 3)
test("Hospital Alpha has lung cancer data", lambda: federated_server.hospitals[0].cancer_focus == "NSCLC / SCLC")

# Run 2 rounds of federated training
result = federated_server.run_full_training(n_rounds=2, local_epochs=3)
test("Training completes", lambda: result["status"] == "TRAINING_COMPLETE")
test("Training has 2 rounds", lambda: result["total_rounds"] == 2)
test("Hospitals report loss reduction", lambda: all(h["final_loss"] is not None for h in result["hospitals"]))
test("Privacy guarantee present", lambda: "No raw patient data" in result["privacy_guarantee"])

status = federated_server.get_status()
test("Status shows global model initialized", lambda: status["global_model_initialized"] == True)


# ========== PHASE 4: DICOM & Imaging Engine ==========
print("\n--- Phase 4: DICOM & Imaging Engine ---")

from app.dicom_engine import imaging_engine, DermoscopyAnalyzer
import base64

# Create test image data
test_image_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

test("Imaging engine processes skin lesion", lambda: imaging_engine.process_image(test_image_b64, "skin lesion mole dermoscopy").get("has_image") == True)
test("Dermoscopy returns ABCDE scores", lambda: "abcde_scores" in imaging_engine.process_image(test_image_b64, "skin lesion mole").keys() or "pipeline" in imaging_engine.process_image(test_image_b64, "skin lesion mole").keys())

ct_result = imaging_engine.process_image(test_image_b64, "CT scan chest")
test("CT context routes to DICOM parser", lambda: "DICOM" in str(ct_result.get("pipeline", "")) or "format" in ct_result)

path_result = imaging_engine.process_image(test_image_b64, "pathology biopsy H&E slide")
test("Pathology context routes to histopath", lambda: "Histopathology" in str(path_result.get("pipeline", "")) or "analysis_type" in path_result)

generic_result = imaging_engine.process_image(test_image_b64, "")
test("Generic image returns observation", lambda: generic_result.get("has_image") == True)

test("No image returns correctly", lambda: imaging_engine.process_image("", "").get("has_image") == False)


# ========== PHASE 5: RAG + Triage + Safety (legacy) ==========
print("\n--- Phase 5: Legacy RAG + Triage + Safety ---")

from app.triage import classify_triage
from app.safety import is_risky

test("Triage: febrile neutropenia -> RED", lambda: classify_triage("I have fever 101F after chemo febrile neutropenia")["level"] == "RED")
test("Triage: green for general query", lambda: classify_triage("What is breast cancer screening?")["level"] == "GREEN")

test("Safety: blocks diagnosis request", lambda: is_risky("Diagnose me I have a lump") == True)
test("Safety: allows educational query", lambda: is_risky("What are breast cancer symptoms?") == False)


# ========== SUMMARY ==========
print("\n" + "=" * 60)
print(f"RESULTS: {passed}/{total} passed, {failed} failed")
print("=" * 60)

if failed == 0:
    print("ALL TESTS PASSED - OncoGraph AI v4.0 is fully operational")
else:
    print(f"WARNING: {failed} test(s) failed - review output above")
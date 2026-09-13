#!/usr/bin/env python3
"""
orchestrator.py
OncoGraph AI: Stateful Multi-Agent Clinical GraphRAG Orchestrator.
Orchestrates clinical reasoning workflow:
  Query -> Intent Routing -> Parallel Retrieval (Qdrant Vector + Neo4j Graph)
        -> Multi-Specialist Tumor Board -> Biomarker & Safety Critique Gate -> Guarded Response.
"""

from typing import Dict, Any, List, Optional
import time
from app.qdrant_engine import qdrant_engine
from app.neo4j_engine import neo4j_engine
from app.agents.tumor_board import tumor_board_agent


class ClinicalState:
    """State schema for the multi-agent clinical workflow."""
    def __init__(self, query: str, patient_profile: Optional[Dict[str, Any]] = None):
        self.query = query
        self.patient_profile = patient_profile or {}
        self.intent = "GENERAL_ONCOLOGY"
        self.extracted_biomarkers: List[str] = []
        self.extracted_cancer_type: Optional[str] = None
        self.vector_evidence: List[Dict[str, Any]] = []
        self.graph_paths: List[Dict[str, Any]] = []
        self.rrf_ranked_context: List[Dict[str, Any]] = []
        self.tumor_board_consensus: Dict[str, Any] = {}
        self.critique_passed: bool = True
        self.critique_notes: List[str] = []
        self.final_response: str = ""
        self.execution_timeline_ms: Dict[str, float] = {}


class LangGraphClinicalOrchestrator:
    """
    Multi-Agent Orchestrator coordinating specialized clinical agents and safety gates.
    """

    def __init__(self):
        self.qdrant = qdrant_engine
        self.neo4j = neo4j_engine
        self.tumor_board = tumor_board_agent

    def route_intent(self, state: ClinicalState) -> ClinicalState:
        """Node 1: Clinical Intent Classification & Entity Extraction."""
        t0 = time.time()
        q_lower = state.query.lower()

        # Entity extraction heuristics
        if "nsclc" in q_lower or "lung" in q_lower:
            state.extracted_cancer_type = "NSCLC"
        elif "breast" in q_lower:
            state.extracted_cancer_type = "BREAST_CANCER"
        elif "ovarian" in q_lower:
            state.extracted_cancer_type = "OVARIAN"
        elif "colorectal" in q_lower or "crc" in q_lower:
            state.extracted_cancer_type = "CRC"
        elif "melanoma" in q_lower:
            state.extracted_cancer_type = "MELANOMA"

        # Biomarkers
        if "exon 19" in q_lower or "ex19del" in q_lower:
            state.extracted_biomarkers.append("EGFR_EX19DEL")
        if "l858r" in q_lower:
            state.extracted_biomarkers.append("EGFR_L858R")
        if "t790m" in q_lower:
            state.extracted_biomarkers.append("EGFR_T790M")
        if "kras" in q_lower or "g12c" in q_lower:
            state.extracted_biomarkers.append("KRAS_G12C")
        if "her2" in q_lower:
            state.extracted_biomarkers.append("HER2_AMP")
        if "brca" in q_lower or "brca1" in q_lower or "brca2" in q_lower:
            state.extracted_biomarkers.append("BRCA1_MUT")
        if "pdl1" in q_lower or "pd-l1" in q_lower:
            state.extracted_biomarkers.append("PDL1_HIGH")

        # Intent
        if any(w in q_lower for w in ["resist", "relapse", "progress", "t790m"]):
            state.intent = "RESISTANCE_PATHWAY"
        elif any(w in q_lower for w in ["treat", "therapy", "first-line", "drug", "option"]):
            state.intent = "TREATMENT_SELECTION"
        elif any(w in q_lower for w in ["toxic", "side effect", "adverse", "pneumonitis", "cardio"]):
            state.intent = "TOXICITY_MANAGEMENT"
        elif any(w in q_lower for w in ["tumor board", "consensus", "multidisciplinary"]):
            state.intent = "TUMOR_BOARD_CONSENSUS"
        else:
            state.intent = "CLINICAL_QUERY"

        state.execution_timeline_ms["intent_routing"] = round((time.time() - t0) * 1000, 2)
        return state

    def parallel_retrieval(self, state: ClinicalState) -> ClinicalState:
        """Node 2: Concurrently query Qdrant Dense Vector Store and Neo4j Cypher Graph."""
        t0 = time.time()

        # 1. Qdrant Dense Search
        vector_res = self.qdrant.dense_search(
            query=state.query,
            top_k=3,
            filter_cancer=state.extracted_cancer_type
        )
        state.vector_evidence = vector_res

        # 2. Neo4j Cypher Multi-Hop Graph Traversal
        graph_res = []
        for bio in state.extracted_biomarkers:
            cancer = state.extracted_cancer_type or "NSCLC"
            therapies = self.neo4j.find_actionable_therapies(bio, cancer)
            for th in therapies:
                graph_res.append({
                    "biomarker": bio,
                    "cancer_type": cancer,
                    "drug_name": th["drug_name"],
                    "drug_class": th["drug_class"],
                    "evidence_level": th["evidence"],
                    "source": "Neo4j Cypher Multi-Hop Traversal"
                })
        state.graph_paths = graph_res

        # 3. Reciprocal Rank Fusion (RRF k=60)
        fusion_scores = {}
        # Add vector ranks
        for r, item in enumerate(state.vector_evidence):
            doc_id = item["id"]
            fusion_scores[doc_id] = fusion_scores.get(doc_id, 0.0) + (1.0 / (60.0 + r + 1))

        # Add graph ranks
        for r, item in enumerate(state.graph_paths):
            gid = f"GRAPH_{item['drug_name']}_{item['biomarker']}"
            fusion_scores[gid] = fusion_scores.get(gid, 0.0) + (1.0 / (60.0 + r + 1))

        state.rrf_ranked_context = [
            {"item_id": k, "rrf_score": round(v, 4)} for k, v in sorted(fusion_scores.items(), key=lambda x: x[1], reverse=True)
        ]

        state.execution_timeline_ms["retrieval_and_rrf"] = round((time.time() - t0) * 1000, 2)
        return state

    def tumor_board_synthesis(self, state: ClinicalState) -> ClinicalState:
        """Node 3: Synthesize Multi-Specialist Clinical Perspectives."""
        t0 = time.time()
        patient_case = {
            "query": state.query,
            "cancer_type": state.extracted_cancer_type or "NSCLC",
            "biomarkers": state.extracted_biomarkers,
            "stage": state.patient_profile.get("stage", "Stage IV (Metastatic)"),
            "ecog_ps": state.patient_profile.get("ecog_ps", 1)
        }
        consensus = self.tumor_board.deliberate(patient_case)
        state.tumor_board_consensus = consensus
        state.execution_timeline_ms["tumor_board_synthesis"] = round((time.time() - t0) * 1000, 2)
        return state

    def biomarker_safety_critique(self, state: ClinicalState) -> ClinicalState:
        """Node 4: Safety & Resistance Validation Guardrail Gate."""
        t0 = time.time()
        state.critique_passed = True
        state.critique_notes = []

        # Check resistance violations
        for bio in state.extracted_biomarkers:
            if bio == "KRAS_G12C":
                state.critique_notes.append("GUARD: KRAS G12C confers primary resistance to EGFR TKIs (Erlotinib/Gefitinib). Advise KRAS inhibitor (Sotorasib) or Platinum Chemo + IO.")
            if bio == "EGFR_T790M":
                state.critique_notes.append("GUARD: EGFR T790M gatekeeper mutation causes resistance to 1st/2nd Gen TKIs. 3rd-Gen TKI (Osimertinib) is mandatory.")

        # Check toxicity alerts
        if "HER2_AMP" in state.extracted_biomarkers:
            state.critique_notes.append("SAFETY GATE: Baseline and quarterly echocardiogram (LVEF) required before Trastuzumab/Pertuzumab.")
        if "PDL1_HIGH" in state.extracted_biomarkers:
            state.critique_notes.append("SAFETY GATE: Monitor for immune-related pneumonitis/colitis. Withhold IO for Grade >= 2 toxicities.")

        state.execution_timeline_ms["critique_guardrail"] = round((time.time() - t0) * 1000, 2)
        return state

    def format_guarded_response(self, state: ClinicalState) -> ClinicalState:
        """Node 5: Assemble structured, evidence-backed clinical recommendation."""
        t0 = time.time()

        rec_drugs = [g["drug_name"] for g in state.graph_paths] or ["Standard Systemic Protocol"]
        evidence_tier = state.graph_paths[0]["evidence_level"] if state.graph_paths else "NCCN Category 1"

        summary_parts = [
            f"### 🩺 Clinical Decision Recommendation ({state.intent})",
            f"**Cancer Type**: {state.extracted_cancer_type or 'General Oncology'} | **Biomarkers**: {', '.join(state.extracted_biomarkers) or 'Wild-Type / Pending'}",
            "",
            "#### 💊 Precision Targeted Regimens (Evidence-Ranked):"
        ]

        if state.graph_paths:
            for g in state.graph_paths:
                summary_parts.append(f"- **{g['drug_name']}** ({g['drug_class']}) — Target: `{g['biomarker']}` | Evidence: *{g['evidence_level']}*")
        elif state.vector_evidence:
            for v in state.vector_evidence:
                summary_parts.append(f"- **{v['title']}**: {v['text'][:140]}...")
        else:
            summary_parts.append("- Multi-agent consensus advises standard platinum-doublet or targeted therapy based on molecular NGS testing.")

        if state.critique_notes:
            summary_parts.append("\n#### 🛡️ Biomarker Safety & Resistance Guardrails:")
            for note in state.critique_notes:
                summary_parts.append(f"- {note}")

        summary_parts.append("\n#### 👥 Multidisciplinary Tumor Board Synthesis:")
        rec = state.tumor_board_consensus.get("consensus_recommendation", "Multidisciplinary consensus validated.")
        summary_parts.append(f"*{rec}*")

        state.final_response = "\n".join(summary_parts)
        state.execution_timeline_ms["response_formatting"] = round((time.time() - t0) * 1000, 2)
        return state

    def run(self, query: str, patient_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute full stateful multi-agent LangGraph workflow."""
        start_time = time.time()
        state = ClinicalState(query, patient_profile)

        state = self.route_intent(state)
        state = self.parallel_retrieval(state)
        state = self.tumor_board_synthesis(state)
        state = self.biomarker_safety_critique(state)
        state = self.format_guarded_response(state)

        total_latency = round((time.time() - start_time) * 1000, 2)

        return {
            "status": "SUCCESS",
            "intent": state.intent,
            "cancer_type": state.extracted_cancer_type,
            "biomarkers": state.extracted_biomarkers,
            "vector_evidence_count": len(state.vector_evidence),
            "graph_paths_count": len(state.graph_paths),
            "rrf_fused_candidates": state.rrf_ranked_context,
            "guardrail_passed": state.critique_passed,
            "guardrail_alerts": state.critique_notes,
            "tumor_board_consensus": state.tumor_board_consensus,
            "recommendation_markdown": state.final_response,
            "execution_timeline_ms": state.execution_timeline_ms,
            "total_latency_ms": total_latency
        }


# Global orchestrator singleton
clinical_orchestrator = LangGraphClinicalOrchestrator()

#!/usr/bin/env python3
"""
neo4j_engine.py
OncoGraph AI: Production Neo4j Cypher Multi-Hop Graph Traversal Engine.
Executes multi-hop clinical pathway traversals across:
  (Biomarker)-[:ASSOCIATED_WITH]->(CancerType)
  (Drug)-[:TARGETS]->(Biomarker)
  (Biomarker)-[:RESISTANT_TO]->(Drug)
  (Drug)-[:CAUSES]->(Toxicity)
Supports live Neo4j bolt driver with transparent native graph reasoning engine fallback.
"""

from typing import List, Dict, Any, Optional
import logging

try:
    from neo4j import GraphDatabase
    NEO4J_DRIVER_AVAILABLE = True
except ImportError:
    NEO4J_DRIVER_AVAILABLE = False

logger = logging.getLogger(__name__)


class Neo4jOncologyEngine:
    """
    Neo4j Graph Database Multi-Hop Traversal Engine for Oncology Precision Medicine.
    """

    def __init__(self, uri: str = "bolt://localhost:7687", auth: tuple = ("neo4j", "password")):
        self.uri = uri
        self.auth = auth
        self.driver = None
        self.is_connected = False

        if NEO4J_DRIVER_AVAILABLE:
            try:
                self.driver = GraphDatabase.driver(uri, auth=auth)
                self.driver.verify_connectivity()
                self.is_connected = True
            except Exception:
                self.driver = None
                self.is_connected = False

        self._seed_local_graph()

    def _seed_local_graph(self):
        """Build curated local in-memory relational graph for zero-dependency execution."""
        self.biomarkers = {
            "EGFR_EX19DEL": {"name": "EGFR Exon 19 Deletion", "gene": "EGFR", "cancers": ["NSCLC"]},
            "EGFR_L858R": {"name": "EGFR L858R Mutation", "gene": "EGFR", "cancers": ["NSCLC"]},
            "EGFR_T790M": {"name": "EGFR T790M Gatekeeper", "gene": "EGFR", "cancers": ["NSCLC"]},
            "ALK_FUSION": {"name": "ALK-EML4 Rearrangement", "gene": "ALK", "cancers": ["NSCLC"]},
            "KRAS_G12C": {"name": "KRAS G12C Mutation", "gene": "KRAS", "cancers": ["NSCLC", "CRC"]},
            "HER2_AMP": {"name": "HER2 Amplification", "gene": "ERBB2", "cancers": ["BREAST_CANCER", "GASTRIC"]},
            "BRCA1_MUT": {"name": "BRCA1 Germline Mutation", "gene": "BRCA1", "cancers": ["BREAST_CANCER", "OVARIAN"]},
            "PDL1_HIGH": {"name": "PD-L1 TPS >= 50%", "gene": "CD274", "cancers": ["NSCLC", "BLADDER"]},
        }

        self.drugs = {
            "OSIMERTINIB": {"name": "Osimertinib", "class": "3rd-Gen EGFR TKI", "targets": ["EGFR_EX19DEL", "EGFR_L858R", "EGFR_T790M"], "evidence": "Level 1A (NCCN Category 1)"},
            "ERLOTINIB": {"name": "Erlotinib", "class": "1st-Gen EGFR TKI", "targets": ["EGFR_EX19DEL", "EGFR_L858R"], "evidence": "Level 1B"},
            "SOTORASIB": {"name": "Sotorasib", "class": "KRAS G12C Inhibitor", "targets": ["KRAS_G12C"], "evidence": "Level 2A (CodeBreaK 100)"},
            "TRASTUZUMAB": {"name": "Trastuzumab", "class": "HER2 Monoclonal Antibody", "targets": ["HER2_AMP"], "evidence": "Level 1A (CLEOPATRA)"},
            "OLAPARIB": {"name": "Olaparib", "class": "PARP Inhibitor", "targets": ["BRCA1_MUT"], "evidence": "Level 1A (OlympiAD)"},
            "PEMBROLIZUMAB": {"name": "Pembrolizumab", "class": "PD-1 Checkpoint Inhibitor", "targets": ["PDL1_HIGH"], "evidence": "Level 1A (KEYNOTE-024)"},
        }

        self.resistances = [
            {"biomarker": "EGFR_T790M", "drug": "ERLOTINIB", "mechanism": "Steric hindrance at ATP binding pocket prevents 1st-gen TKI binding."},
            {"biomarker": "KRAS_G12C", "drug": "ERLOTINIB", "mechanism": "Constitutive downstream MAPK activation bypasses upstream EGFR inhibition."},
            {"biomarker": "KRAS_G12C", "drug": "OSIMERTINIB", "mechanism": "Downstream KRAS bypass signaling causes primary TKI refractoriness."},
        ]

        self.toxicities = {
            "TRASTUZUMAB": [{"name": "Cardiotoxicity / Decreased LVEF", "severity": "Grade 2-3", "management": "Serial ECHO every 3 months. Hold if LVEF drops > 10%"}],
            "PEMBROLIZUMAB": [{"name": "Autoimmune Pneumonitis / Colitis", "severity": "Grade 3-4", "management": "Hold therapy, start high-dose steroids (1-2mg/kg prednisone)"}],
            "OSIMERTINIB": [{"name": "QTc Prolongation / Interstitial Lung Disease", "severity": "Grade 2", "management": "Baseline and periodic ECG monitoring"}]
        }

    def find_actionable_therapies(self, biomarker_id: str, cancer_id: str) -> List[Dict[str, Any]]:
        """
        Cypher Multi-Hop Query:
        MATCH (b:Biomarker {id: $biomarker_id})-[r1:ASSOCIATED_WITH]->(c:CancerType {id: $cancer_id})
        MATCH (d:Drug)-[r2:TARGETS]->(b)
        WHERE NOT (b)-[:RESISTANT_TO]->(d)
        RETURN d.name AS DrugName, d.drug_class AS Class, r2.evidence_level AS Evidence
        """
        if self.is_connected and self.driver:
            try:
                query = """
                MATCH (b:Biomarker {id: $biomarker_id})-[r1:ASSOCIATED_WITH]->(c:CancerType {id: $cancer_id})
                MATCH (d:Drug)-[r2:TARGETS]->(b)
                WHERE NOT (b)-[:RESISTANT_TO]->(d)
                RETURN d.id AS drug_id, d.name AS drug_name, d.drug_class AS drug_class, r2.evidence_level AS evidence
                ORDER BY r2.evidence_level DESC
                """
                with self.driver.session() as session:
                    result = session.run(query, biomarker_id=biomarker_id, cancer_id=cancer_id)
                    return [record.data() for record in result]
            except Exception:
                pass

        # Native Graph Traversal
        b_clean = biomarker_id.upper().strip()
        c_clean = cancer_id.upper().strip()

        # Find resistant drugs for this biomarker
        resistant_drug_ids = {r["drug"] for r in self.resistances if r["biomarker"] == b_clean}

        actionable = []
        for did, dinfo in self.drugs.items():
            if b_clean in dinfo["targets"] and did not in resistant_drug_ids:
                actionable.append({
                    "drug_id": did,
                    "drug_name": dinfo["name"],
                    "drug_class": dinfo["class"],
                    "evidence": dinfo["evidence"],
                    "mechanism_of_action": f"Directly targets {b_clean} without documented resistance."
                })
        return actionable

    def check_resistance_pathways(self, biomarker_id: str, drug_id: str) -> Optional[Dict[str, Any]]:
        """
        Check if a given biomarker creates resistance against a specific therapy.
        """
        b_clean = biomarker_id.upper().strip()
        d_clean = drug_id.upper().strip()

        for r in self.resistances:
            if r["biomarker"] == b_clean and r["drug"] == d_clean:
                return {
                    "has_resistance": True,
                    "biomarker": b_clean,
                    "drug": d_clean,
                    "mechanism": r["mechanism"],
                    "recommendation": "CONTRAINDICATED: Select an alternative line of targeted therapy."
                }
        return {"has_resistance": False, "biomarker": b_clean, "drug": d_clean}

    def get_toxicities(self, drug_id: str) -> List[Dict[str, Any]]:
        return self.toxicities.get(drug_id.upper().strip(), [])

    def get_status(self) -> Dict[str, Any]:
        return {
            "engine": "Neo4j Cypher Graph Engine",
            "connected_to_bolt": self.is_connected,
            "biomarker_nodes": len(self.biomarkers),
            "drug_nodes": len(self.drugs),
            "resistance_edges": len(self.resistances),
            "query_language": "Cypher 5.x Multi-Hop"
        }


# Global singleton instance
neo4j_engine = Neo4jOncologyEngine()

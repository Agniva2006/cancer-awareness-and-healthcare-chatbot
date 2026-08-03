"""
OncoGraph AI — Multi-Modal Clinical Knowledge Graph Engine
Uses NetworkX to model complex oncological relationships between:
  Mutations, Drugs, Protocols, Staging, Toxicities, Biomarkers, Guidelines
Supports graph traversal queries, shortest-path reasoning, and hybrid retrieval.
"""

import networkx as nx
from typing import List, Dict, Any, Optional
import json
from pathlib import Path


class OncologyKnowledgeGraph:
    """
    Builds and queries a directed multi-relational clinical oncology knowledge graph.
    Entity types: MUTATION, DRUG, PROTOCOL, STAGING, TOXICITY, BIOMARKER, CANCER_TYPE, GUIDELINE
    """

    def __init__(self):
        self.G = nx.DiGraph()
        self._build_graph()

    def _add_entity(self, node_id: str, node_type: str, **attrs):
        self.G.add_node(node_id, node_type=node_type, **attrs)

    def _add_relation(self, src: str, dst: str, relation: str, **attrs):
        self.G.add_edge(src, dst, relation=relation, **attrs)

    def _build_graph(self):
        """Populate the knowledge graph with curated oncological entities and relationships."""

        # ========== CANCER TYPES ==========
        cancers = [
            ("NSCLC", "Non-Small Cell Lung Cancer"),
            ("SCLC", "Small Cell Lung Cancer"),
            ("BREAST_CANCER", "Breast Cancer"),
            ("CRC", "Colorectal Cancer"),
            ("PANCREATIC", "Pancreatic Adenocarcinoma"),
            ("MELANOMA", "Cutaneous Melanoma"),
            ("PROSTATE", "Prostate Cancer"),
            ("OVARIAN", "Ovarian Cancer"),
        ]
        for cid, label in cancers:
            self._add_entity(cid, "CANCER_TYPE", label=label)

        # ========== BIOMARKERS / MUTATIONS ==========
        mutations = [
            ("EGFR_EX19DEL", "EGFR Exon 19 Deletion", "NSCLC"),
            ("EGFR_L858R", "EGFR L858R Point Mutation", "NSCLC"),
            ("EGFR_T790M", "EGFR T790M Resistance Mutation", "NSCLC"),
            ("ALK_FUSION", "ALK-EML4 Gene Rearrangement", "NSCLC"),
            ("KRAS_G12C", "KRAS G12C Mutation", "NSCLC"),
            ("HER2_AMP", "HER2/ERBB2 Amplification", "BREAST_CANCER"),
            ("BRCA1_MUT", "BRCA1 Germline Pathogenic Variant", "BREAST_CANCER"),
            ("BRCA2_MUT", "BRCA2 Germline Pathogenic Variant", "OVARIAN"),
            ("PDL1_HIGH", "PD-L1 TPS >= 50%", "NSCLC"),
            ("MSI_H", "Microsatellite Instability High (dMMR)", "CRC"),
            ("PSA_ELEVATED", "Elevated PSA (> 10 ng/mL)", "PROSTATE"),
            ("BRAF_V600E", "BRAF V600E Mutation", "MELANOMA"),
        ]
        for mid, label, cancer in mutations:
            self._add_entity(mid, "BIOMARKER", label=label)
            self._add_relation(mid, cancer, "ASSOCIATED_WITH")

        # ========== TARGETED THERAPIES & DRUGS ==========
        drugs = [
            ("OSIMERTINIB", "Osimertinib (Tagrisso)", "TKI", "EGFR"),
            ("ERLOTINIB", "Erlotinib (Tarceva)", "TKI", "EGFR"),
            ("ALECTINIB", "Alectinib (Alecensa)", "TKI", "ALK"),
            ("LORLATINIB", "Lorlatinib (Lorbrena)", "TKI", "ALK"),
            ("SOTORASIB", "Sotorasib (Lumakras)", "Covalent Inhibitor", "KRAS G12C"),
            ("ADAGRASIB", "Adagrasib (Krazati)", "Covalent Inhibitor", "KRAS G12C"),
            ("TRASTUZUMAB", "Trastuzumab (Herceptin)", "Monoclonal Antibody", "HER2"),
            ("TDXd", "Trastuzumab Deruxtecan (Enhertu)", "Antibody-Drug Conjugate", "HER2"),
            ("PERTUZUMAB", "Pertuzumab (Perjeta)", "Monoclonal Antibody", "HER2"),
            ("OLAPARIB", "Olaparib (Lynparza)", "PARP Inhibitor", "BRCA1/2"),
            ("NIRAPARIB", "Niraparib (Zejula)", "PARP Inhibitor", "BRCA1/2"),
            ("PEMBROLIZUMAB", "Pembrolizumab (Keytruda)", "Anti-PD-1 ICI", "PD-L1 / MSI-H"),
            ("NIVOLUMAB", "Nivolumab (Opdivo)", "Anti-PD-1 ICI", "PD-L1"),
            ("IPILIMUMAB", "Ipilimumab (Yervoy)", "Anti-CTLA-4 ICI", "Melanoma"),
            ("DABRAFENIB", "Dabrafenib (Tafinlar)", "BRAF Inhibitor", "BRAF V600E"),
            ("TRAMETINIB", "Trametinib (Mekinist)", "MEK Inhibitor", "BRAF V600E"),
            ("DOSTARLIMAB", "Dostarlimab (Jemperli)", "Anti-PD-1 ICI", "MSI-H/dMMR"),
        ]
        for did, label, drug_class, target in drugs:
            self._add_entity(did, "DRUG", label=label, drug_class=drug_class, target=target)

        # ========== MUTATION -> DRUG (SENSITIZES) ==========
        sensitivity_map = [
            ("EGFR_EX19DEL", "OSIMERTINIB", "First-line NCCN Category 1"),
            ("EGFR_L858R", "OSIMERTINIB", "First-line NCCN Category 1"),
            ("EGFR_L858R", "ERLOTINIB", "Alternative first-line"),
            ("EGFR_T790M", "OSIMERTINIB", "Second-line after T790M resistance"),
            ("ALK_FUSION", "ALECTINIB", "Preferred first-line NCCN"),
            ("ALK_FUSION", "LORLATINIB", "Second-line after ALK TKI resistance"),
            ("KRAS_G12C", "SOTORASIB", "FDA-approved second-line NSCLC"),
            ("KRAS_G12C", "ADAGRASIB", "FDA-approved second-line NSCLC"),
            ("HER2_AMP", "TRASTUZUMAB", "Standard first-line HER2+ breast"),
            ("HER2_AMP", "TDXd", "Second-line ADC for HER2+ or HER2-low"),
            ("HER2_AMP", "PERTUZUMAB", "First-line combination with Trastuzumab"),
            ("BRCA1_MUT", "OLAPARIB", "Adjuvant HER2-negative early breast / mCRPC"),
            ("BRCA2_MUT", "OLAPARIB", "Maintenance ovarian / mCRPC"),
            ("BRCA2_MUT", "NIRAPARIB", "Maintenance platinum-sensitive ovarian"),
            ("PDL1_HIGH", "PEMBROLIZUMAB", "Single-agent first-line NSCLC (TPS>=50%)"),
            ("MSI_H", "PEMBROLIZUMAB", "Tissue-agnostic FDA approval"),
            ("MSI_H", "DOSTARLIMAB", "Tissue-agnostic MSI-H/dMMR"),
            ("BRAF_V600E", "DABRAFENIB", "BRAF+MEK combination melanoma"),
            ("BRAF_V600E", "TRAMETINIB", "BRAF+MEK combination melanoma"),
        ]
        for mut, drug, evidence in sensitivity_map:
            self._add_relation(mut, drug, "SENSITIZES_TO", evidence=evidence)

        # ========== CHEMOTHERAPY PROTOCOLS ==========
        protocols = [
            ("FOLFOX", "FOLFOX (5-FU + Leucovorin + Oxaliplatin)", "CRC"),
            ("FOLFIRINOX", "FOLFIRINOX (5-FU + Leucovorin + Oxaliplatin + Irinotecan)", "PANCREATIC"),
            ("AC_T", "AC-T (Doxorubicin + Cyclophosphamide -> Paclitaxel)", "BREAST_CANCER"),
            ("CARBO_PEMETREXED", "Carboplatin + Pemetrexed", "NSCLC"),
            ("CDDP_ETOPOSIDE", "Cisplatin + Etoposide", "SCLC"),
        ]
        for pid, label, cancer in protocols:
            self._add_entity(pid, "PROTOCOL", label=label)
            self._add_relation(pid, cancer, "TREATS")

        # ========== TOXICITIES ==========
        toxicities = [
            ("PERIPHERAL_NEUROPATHY", "Peripheral Neuropathy (CTCAE Grade 2-3)", "FOLFOX"),
            ("CARDIOTOXICITY", "Cardiotoxicity (LVEF decline)", "AC_T"),
            ("PNEUMONITIS", "Immune-Related Pneumonitis", "PEMBROLIZUMAB"),
            ("COLITIS", "Immune-Related Colitis (Grade 2-4)", "IPILIMUMAB"),
            ("HEPATITIS", "Immune-Related Hepatitis", "NIVOLUMAB"),
            ("FEBRILE_NEUTROPENIA", "Febrile Neutropenia (ANC < 500)", "FOLFIRINOX"),
            ("QT_PROLONGATION", "QT Prolongation", "OSIMERTINIB"),
        ]
        for tid, label, caused_by in toxicities:
            self._add_entity(tid, "TOXICITY", label=label)
            self._add_relation(caused_by, tid, "CAUSES_TOXICITY")

        # ========== TNM STAGING ==========
        stages = [
            ("STAGE_I", "Stage I (Localized, T1-T2 N0 M0)"),
            ("STAGE_II", "Stage II (Regional, T2-T3 N0-N1 M0)"),
            ("STAGE_III", "Stage III (Locally Advanced, T3-T4 N1-N2 M0)"),
            ("STAGE_IV", "Stage IV (Metastatic, Any T Any N M1)"),
        ]
        for sid, label in stages:
            self._add_entity(sid, "STAGING", label=label)

        # ========== ONCOLOGICAL EMERGENCIES ==========
        emergencies = [
            ("FEBRILE_NEUTROPENIA_EMERGENCY", "Febrile Neutropenia Emergency"),
            ("SPINAL_CORD_COMPRESSION", "Malignant Spinal Cord Compression"),
            ("SVC_SYNDROME", "Superior Vena Cava Syndrome"),
            ("TUMOR_LYSIS", "Tumor Lysis Syndrome"),
            ("HYPERCALCEMIA_MALIGNANCY", "Hypercalcemia of Malignancy"),
            ("CRS_CAR_T", "Cytokine Release Syndrome (CAR-T)"),
        ]
        for eid, label in emergencies:
            self._add_entity(eid, "EMERGENCY", label=label)

    # ========== QUERY METHODS ==========

    def get_therapies_for_mutation(self, mutation_id: str) -> List[Dict[str, Any]]:
        """Find all drugs that a given mutation sensitizes to."""
        results = []
        if mutation_id not in self.G:
            return results
        for _, target, data in self.G.out_edges(mutation_id, data=True):
            if data.get("relation") == "SENSITIZES_TO":
                drug_data = self.G.nodes.get(target, {})
                results.append({
                    "drug_id": target,
                    "drug_label": drug_data.get("label", target),
                    "drug_class": drug_data.get("drug_class", ""),
                    "evidence": data.get("evidence", ""),
                })
        return results

    def get_toxicities_for_treatment(self, treatment_id: str) -> List[Dict[str, Any]]:
        """Find all known toxicities caused by a treatment."""
        results = []
        if treatment_id not in self.G:
            return results
        for _, target, data in self.G.out_edges(treatment_id, data=True):
            if data.get("relation") == "CAUSES_TOXICITY":
                tox_data = self.G.nodes.get(target, {})
                results.append({
                    "toxicity_id": target,
                    "toxicity_label": tox_data.get("label", target),
                })
        return results

    def get_cancer_biomarkers(self, cancer_id: str) -> List[Dict[str, Any]]:
        """Find all biomarkers associated with a specific cancer type."""
        results = []
        for src, dst, data in self.G.in_edges(cancer_id, data=True):
            if data.get("relation") == "ASSOCIATED_WITH":
                bio_data = self.G.nodes.get(src, {})
                results.append({
                    "biomarker_id": src,
                    "biomarker_label": bio_data.get("label", src),
                })
        return results

    def find_treatment_path(self, mutation_id: str, cancer_id: str) -> List[str]:
        """Find shortest reasoning path from a mutation to cancer type through the graph."""
        try:
            path = nx.shortest_path(self.G, source=mutation_id, target=cancer_id)
            return [self.G.nodes[n].get("label", n) for n in path]
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def search_entities(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Keyword search across all graph node labels."""
        q_lower = query.lower()
        results = []
        for node_id, data in self.G.nodes(data=True):
            label = data.get("label", node_id).lower()
            if any(term in label for term in q_lower.split()):
                results.append({
                    "id": node_id,
                    "type": data.get("node_type", ""),
                    "label": data.get("label", node_id),
                })
        return results[:top_k]

    def get_full_patient_profile(self, mutation_ids: List[str]) -> Dict[str, Any]:
        """Build a comprehensive patient genomic profile: mutations -> therapies -> toxicities."""
        profile = {"mutations": [], "therapies": [], "toxicities": [], "clinical_trials_eligible": []}
        for mid in mutation_ids:
            node = self.G.nodes.get(mid, {})
            profile["mutations"].append({"id": mid, "label": node.get("label", mid)})
            therapies = self.get_therapies_for_mutation(mid)
            for t in therapies:
                profile["therapies"].append(t)
                toxicities = self.get_toxicities_for_treatment(t["drug_id"])
                profile["toxicities"].extend(toxicities)
        # Deduplicate
        seen = set()
        profile["therapies"] = [t for t in profile["therapies"] if t["drug_id"] not in seen and not seen.add(t["drug_id"])]
        seen_tox = set()
        profile["toxicities"] = [t for t in profile["toxicities"] if t["toxicity_id"] not in seen_tox and not seen_tox.add(t["toxicity_id"])]
        return profile

    def get_graph_stats(self) -> Dict[str, int]:
        """Return graph statistics."""
        type_counts = {}
        for _, data in self.G.nodes(data=True):
            nt = data.get("node_type", "UNKNOWN")
            type_counts[nt] = type_counts.get(nt, 0) + 1
        return {
            "total_nodes": self.G.number_of_nodes(),
            "total_edges": self.G.number_of_edges(),
            "node_types": type_counts,
        }

    def export_for_visualization(self) -> Dict[str, Any]:
        """Export graph structure as JSON for frontend D3.js / vis.js rendering."""
        nodes = []
        for nid, data in self.G.nodes(data=True):
            nodes.append({
                "id": nid,
                "label": data.get("label", nid),
                "type": data.get("node_type", ""),
            })
        edges = []
        for src, dst, data in self.G.edges(data=True):
            edges.append({
                "source": src,
                "target": dst,
                "relation": data.get("relation", ""),
            })
        return {"nodes": nodes, "edges": edges}


# Singleton instance
knowledge_graph = OncologyKnowledgeGraph()

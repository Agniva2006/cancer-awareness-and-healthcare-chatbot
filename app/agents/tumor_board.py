"""
OncoGraph AI — Multi-Agent Virtual Tumor Board
Implements a swarm of specialized oncological agents that collaborate
to produce a comprehensive clinical decision-support report.

Agents:
  1. TriageAgent        — Emergency risk classification
  2. GenomicAgent       — NGS biomarker to FDA therapy mapping
  3. TrialMatcherAgent  — Clinical trial eligibility screening
  4. ToxicologyAgent    — Drug interaction & CTCAE toxicity analysis
  5. TumorBoardOrchestrator — Aggregates agent outputs into consensus report
"""

from typing import Dict, Any, List, Optional
from app.graph_engine import knowledge_graph
from app.triage import classify_triage


# ===== AGENT BASE =====
class BaseAgent:
    name: str = "BaseAgent"
    role: str = ""

    def analyze(self, patient_context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


# ===== AGENT 1: TRIAGE & EMERGENCY =====
class TriageAgent(BaseAgent):
    name = "Triage & Emergency Agent"
    role = "Evaluates acute clinical risk and flags oncological emergencies"

    def analyze(self, patient_context: Dict[str, Any]) -> Dict[str, Any]:
        query = patient_context.get("query", "")
        symptoms = patient_context.get("symptoms", [])
        combined = f"{query} {' '.join(symptoms)}"
        triage = classify_triage(combined)
        return {
            "agent": self.name,
            "triage_level": triage["level"],
            "title": triage["title"],
            "action": triage["action"],
            "reason": triage["reason"],
        }


# ===== AGENT 2: GENOMIC & BIOMARKER SPECIALIST =====
class GenomicAgent(BaseAgent):
    name = "Genomic & Biomarker Specialist Agent"
    role = "Maps patient mutations to FDA-approved targeted therapies via knowledge graph"

    MUTATION_ALIASES = {
        "egfr exon 19": "EGFR_EX19DEL",
        "egfr l858r": "EGFR_L858R",
        "egfr t790m": "EGFR_T790M",
        "alk fusion": "ALK_FUSION",
        "alk rearrangement": "ALK_FUSION",
        "eml4-alk": "ALK_FUSION",
        "kras g12c": "KRAS_G12C",
        "her2": "HER2_AMP",
        "erbb2": "HER2_AMP",
        "brca1": "BRCA1_MUT",
        "brca2": "BRCA2_MUT",
        "pd-l1": "PDL1_HIGH",
        "pdl1": "PDL1_HIGH",
        "msi-h": "MSI_H",
        "msi high": "MSI_H",
        "dmmr": "MSI_H",
        "braf v600e": "BRAF_V600E",
        "braf": "BRAF_V600E",
        "psa": "PSA_ELEVATED",
    }

    def _resolve_mutations(self, patient_context: Dict[str, Any]) -> List[str]:
        """Resolve free-text mutation mentions to graph node IDs."""
        mutations = patient_context.get("mutations", [])
        query = patient_context.get("query", "").lower()
        resolved = list(mutations)  # pre-specified IDs

        for alias, node_id in self.MUTATION_ALIASES.items():
            if alias in query and node_id not in resolved:
                resolved.append(node_id)

        return resolved

    def analyze(self, patient_context: Dict[str, Any]) -> Dict[str, Any]:
        mutation_ids = self._resolve_mutations(patient_context)
        if not mutation_ids:
            return {
                "agent": self.name,
                "mutations_detected": [],
                "therapies": [],
                "recommendation": "No actionable biomarkers identified. Recommend comprehensive NGS panel testing (e.g. FoundationOne CDx, Tempus xT).",
            }

        profile = knowledge_graph.get_full_patient_profile(mutation_ids)
        return {
            "agent": self.name,
            "mutations_detected": profile["mutations"],
            "therapies": profile["therapies"],
            "toxicities": profile["toxicities"],
            "recommendation": f"Identified {len(profile['therapies'])} FDA-approved targeted therapy options based on {len(mutation_ids)} actionable biomarker(s).",
        }


# ===== AGENT 3: CLINICAL TRIAL MATCHMAKER =====
class TrialMatcherAgent(BaseAgent):
    name = "Clinical Trial Matchmaker Agent"
    role = "Screens patient eligibility against active cancer clinical trials"

    # Simulated trial registry
    TRIAL_REGISTRY = [
        {
            "nct_id": "NCT04487080",
            "title": "Phase III Osimertinib + Savolitinib in EGFR-mutant NSCLC with MET Amplification",
            "biomarkers": ["EGFR_EX19DEL", "EGFR_L858R", "EGFR_T790M"],
            "phase": "Phase III",
            "status": "Recruiting",
        },
        {
            "nct_id": "NCT05609968",
            "title": "KRYSTAL-12: Adagrasib vs Docetaxel in KRAS G12C-Mutant NSCLC",
            "biomarkers": ["KRAS_G12C"],
            "phase": "Phase III",
            "status": "Recruiting",
        },
        {
            "nct_id": "NCT04379596",
            "title": "DESTINY-Breast06: Trastuzumab Deruxtecan in HER2-Low Breast Cancer",
            "biomarkers": ["HER2_AMP"],
            "phase": "Phase III",
            "status": "Active",
        },
        {
            "nct_id": "NCT03170960",
            "title": "KEYNOTE-789: Pembrolizumab + Chemo in EGFR-TKI Resistant NSCLC",
            "biomarkers": ["EGFR_T790M", "PDL1_HIGH"],
            "phase": "Phase III",
            "status": "Recruiting",
        },
        {
            "nct_id": "NCT04165772",
            "title": "OlympiA Extension: Olaparib in gBRCA-mutated High-Risk HER2-Neg Breast",
            "biomarkers": ["BRCA1_MUT", "BRCA2_MUT"],
            "phase": "Phase III",
            "status": "Active",
        },
        {
            "nct_id": "NCT05252390",
            "title": "CheckMate-8HW: Nivolumab+Ipilimumab in dMMR/MSI-H Metastatic CRC",
            "biomarkers": ["MSI_H"],
            "phase": "Phase III",
            "status": "Recruiting",
        },
    ]

    def analyze(self, patient_context: Dict[str, Any]) -> Dict[str, Any]:
        mutation_ids = patient_context.get("mutations", [])
        query = patient_context.get("query", "").lower()

        # Also detect from query text
        genomic = GenomicAgent()
        resolved = genomic._resolve_mutations(patient_context)

        matched_trials = []
        for trial in self.TRIAL_REGISTRY:
            if any(m in trial["biomarkers"] for m in resolved):
                matched_trials.append(trial)

        return {
            "agent": self.name,
            "patient_biomarkers": resolved,
            "matched_trials": matched_trials,
            "total_matches": len(matched_trials),
            "recommendation": f"Patient eligible for {len(matched_trials)} active clinical trial(s)." if matched_trials else "No matching trials found for current biomarker profile.",
        }


# ===== AGENT 4: PHARMACOVIGILANCE & TOXICOLOGY =====
class ToxicologyAgent(BaseAgent):
    name = "Pharmacovigilance & Drug Interaction Agent"
    role = "Evaluates drug-drug interactions, CYP3A4 effects, and CTCAE toxicity risks"

    CYP3A4_INTERACTIONS = {
        "OSIMERTINIB": {
            "inhibitors": ["ketoconazole", "itraconazole", "clarithromycin", "grapefruit"],
            "inducers": ["rifampin", "phenytoin", "carbamazepine", "st john's wort"],
            "effect": "Osimertinib is a CYP3A4 substrate. Strong CYP3A4 inhibitors increase Osimertinib exposure; strong inducers decrease it."
        },
        "OLAPARIB": {
            "inhibitors": ["ketoconazole", "itraconazole", "fluconazole"],
            "inducers": ["rifampin", "phenobarbital"],
            "effect": "Olaparib is metabolized by CYP3A4. Dose reduction required with strong CYP3A4 inhibitors."
        },
        "ALECTINIB": {
            "inhibitors": [],
            "inducers": ["rifampin"],
            "effect": "Alectinib is primarily metabolized by CYP3A4. Avoid strong CYP3A4 inducers."
        },
    }

    def analyze(self, patient_context: Dict[str, Any]) -> Dict[str, Any]:
        co_medications = [m.lower() for m in patient_context.get("co_medications", [])]
        therapy_ids = patient_context.get("therapy_ids", [])

        interactions_found = []
        for drug_id in therapy_ids:
            if drug_id in self.CYP3A4_INTERACTIONS:
                info = self.CYP3A4_INTERACTIONS[drug_id]
                for med in co_medications:
                    if med in info["inhibitors"]:
                        interactions_found.append({
                            "drug": drug_id,
                            "co_medication": med,
                            "type": "CYP3A4 Inhibitor",
                            "risk": "HIGH",
                            "effect": info["effect"],
                        })
                    elif med in info["inducers"]:
                        interactions_found.append({
                            "drug": drug_id,
                            "co_medication": med,
                            "type": "CYP3A4 Inducer",
                            "risk": "HIGH",
                            "effect": info["effect"],
                        })

        # Get toxicities from graph
        toxicities = []
        for drug_id in therapy_ids:
            tox = knowledge_graph.get_toxicities_for_treatment(drug_id)
            toxicities.extend(tox)

        return {
            "agent": self.name,
            "drug_interactions": interactions_found,
            "known_toxicities": toxicities,
            "interaction_count": len(interactions_found),
            "recommendation": f"ALERT: {len(interactions_found)} drug interaction(s) detected." if interactions_found else "No significant drug interactions identified.",
        }


# ===== ORCHESTRATOR: VIRTUAL TUMOR BOARD =====
class TumorBoardOrchestrator:
    """
    Coordinates all specialist agents to produce a unified clinical consensus report,
    mimicking a real multidisciplinary tumor board (MDT) discussion.
    """

    def __init__(self):
        self.agents = [
            TriageAgent(),
            GenomicAgent(),
            TrialMatcherAgent(),
            ToxicologyAgent(),
        ]

    def run_tumor_board(self, patient_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute all agents and aggregate into a tumor board consensus report.

        patient_context should contain:
          - query: str (free-text clinical question)
          - mutations: list[str] (optional pre-identified mutation IDs)
          - symptoms: list[str] (optional symptom descriptions)
          - co_medications: list[str] (optional concurrent medications)
          - cancer_type: str (optional cancer type ID)
          - stage: str (optional stage)
        """
        report = {
            "patient_context": {
                "query": patient_context.get("query", ""),
                "cancer_type": patient_context.get("cancer_type", "Not specified"),
                "stage": patient_context.get("stage", "Not specified"),
            },
            "agent_reports": [],
            "consensus": {},
        }

        # Run each specialist agent
        for agent in self.agents:
            try:
                result = agent.analyze(patient_context)
                report["agent_reports"].append(result)
            except Exception as e:
                report["agent_reports"].append({
                    "agent": agent.name,
                    "error": str(e),
                })

        # Build consensus
        triage_report = report["agent_reports"][0] if report["agent_reports"] else {}
        genomic_report = report["agent_reports"][1] if len(report["agent_reports"]) > 1 else {}
        trial_report = report["agent_reports"][2] if len(report["agent_reports"]) > 2 else {}
        tox_report = report["agent_reports"][3] if len(report["agent_reports"]) > 3 else {}

        report["consensus"] = {
            "triage_level": triage_report.get("triage_level", "GREEN"),
            "actionable_mutations": len(genomic_report.get("mutations_detected", [])),
            "targeted_therapies_available": len(genomic_report.get("therapies", [])),
            "eligible_clinical_trials": trial_report.get("total_matches", 0),
            "drug_interactions_detected": tox_report.get("interaction_count", 0),
            "overall_recommendation": self._generate_recommendation(triage_report, genomic_report, trial_report, tox_report),
        }

        # Enrich with therapy_ids for downstream tox analysis
        if genomic_report.get("therapies"):
            therapy_ids = [t["drug_id"] for t in genomic_report["therapies"]]
            patient_context["therapy_ids"] = therapy_ids
            tox_result = ToxicologyAgent().analyze(patient_context)
            report["agent_reports"][3] = tox_result
            report["consensus"]["drug_interactions_detected"] = tox_result.get("interaction_count", 0)

        return report

    def _generate_recommendation(self, triage, genomic, trial, tox) -> str:
        parts = []

        level = triage.get("triage_level", "GREEN")
        if level == "RED":
            parts.append("URGENT: Immediate emergency medical intervention required before proceeding with treatment planning.")
        elif level == "YELLOW":
            parts.append("ATTENTION: Contact oncology clinic within 24 hours for symptom management.")

        n_therapies = len(genomic.get("therapies", []))
        if n_therapies > 0:
            parts.append(f"Genomic profiling identified {n_therapies} FDA-approved targeted therapy option(s).")
        else:
            parts.append("No actionable biomarkers identified. Recommend comprehensive NGS panel testing.")

        n_trials = trial.get("total_matches", 0)
        if n_trials > 0:
            parts.append(f"Patient is potentially eligible for {n_trials} active clinical trial(s).")

        n_interactions = tox.get("interaction_count", 0)
        if n_interactions > 0:
            parts.append(f"WARNING: {n_interactions} significant drug interaction(s) detected. Review co-medications.")

        return " ".join(parts) if parts else "Standard care pathway recommended."

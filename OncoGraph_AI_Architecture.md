# OncoGraph AI (v4.0 Enterprise) — Clinical Cancer Intelligence Platform

OncoGraph AI is an advanced, multi-modal clinical decision support workspace designed for oncology professionals and medical research networks. The platform transitions from simple conversational systems to a multi-tiered diagnostic intelligence workspace.

---

## 🏛️ Platform Architecture

The system is split into a **Decoupled Server-Client Architecture**:
1. **Frontend**: Static workspace dashboard hosted on **Vercel** (`frontend/` directory).
2. **Backend**: High-performance **FastAPI** API hosted on **Render** (`app/` and `federated/` directories).

```
[ Vercel Hosted Frontend ] (Dashboard Tabs: Chat, Graph, Tumor Board, Federated)
         │
         ▼ (HTTPS JSON REST API Calls)
[ Render Hosted FastAPI Backend ]
         ├── Multi-Modal Knowledge Graph (networkx)
         ├── Multi-Agent Swarm (Genomic, Triage, Trials, Toxicology)
         ├── Simulated Federated Learning Nodes (FedAvg)
         └── DICOM & Visual Diagnostic Engine
```

---

## 📂 Implementation Details by Phase

### 🗂️ Phase 1: Multi-Modal Knowledge Graph Engine (`app/graph_engine.py`)
Models multi-relational clinical oncology connections using **NetworkX**.
- **Nodes (Entity Types)**: `MUTATION`, `DRUG`, `PROTOCOL`, `STAGING`, `TOXICITY`, `BIOMARKER`, `CANCER_TYPE`, `EMERGENCY`.
- **Relationships**:
  - `ASSOCIATED_WITH`: Links mutations/biomarkers to cancer types.
  - `SENSITIZES_TO`: Maps genomic variations to FDA targeted therapies with evidence tags.
  - `TREATS`: Connects chemotherapy protocols to cancer classifications.
  - `CAUSES_TOXICITY`: Pairs therapeutics with CTCAE-graded side effects.
- **Reasoning**: Includes shortest-path traversal queries to link mutations to clinical endpoints, entity search, and D3.js-compatible export for the canvas network visualizer.

### 🤖 Phase 2: Multi-Agent Oncological Swarm (`app/agents/tumor_board.py`)
Simulates a multidisciplinary tumor board (MDT) using 4 dedicated specialist agents:
1. **Triage Agent**: Inspects symptoms/questions for oncological emergencies (e.g. Febrile Neutropenia) and assigns RED/YELLOW alerts.
2. **Genomic Agent**: Resolves text mutation aliases (e.g., "egfr exon 19") to graph IDs and returns FDA targeted therapies.
3. **Trial Matcher Agent**: Cross-references patient mutations against active clinical trials (NCT registries).
4. **Toxicology Agent**: Identifies CYP3A4 drug-drug interactions (e.g. Ketoconazole + Osimertinib TKI exposure risk) and outputs side-effect risk profiles.
- **Orchestrator**: Aggregates all reports into a unified consensus and therapeutic recommendation.

### 🏥 Phase 3: Federated Learning Simulation (`federated/hospital_node.py`)
Simulates distributed machine learning training across three hospital networks without exchanging raw patient health records (PHI), preserving HIPAA compliance:
- **Hospital Alpha (Memorial Cancer Center)**: Lung cancer focus (4,200 samples).
- **Hospital Beta (University Health System)**: Breast cancer focus (3,800 samples).
- **Hospital Gamma (General Research Hospital)**: Colorectal focus (2,900 samples).
- **Algorithm**: Implements **Federated Averaging (FedAvg)**. Weights are simulated as numpy arrays. Each node performs local training epochs on private partitions, and the central server aggregates parameter gradients proportionally to sample size.

### 🖼️ Phase 4: DICOM & Visual Diagnostic Engine (`app/dicom_engine.py`)
Features specialized analysis pipelines for medical imaging formats:
- **DICOM Radiology Parser**: Extracts DICOM metadata header bytes (dimensions, modality, slice thickness).
- **Dermoscopy ABCDE Analyzer**: Scores skin lesion images on Asymmetry, Border irregularity, Color variation, Diameter (mm), and Evolving history to flag melanoma risk.
- **Pathology Stain Scorer**: Analyzes histopathology biopsy H&E/IHC slides for nuclear pleomorphism and tumor-infiltrating lymphocytes.

### 💻 Phase 5: Enterprise Copilot Dashboard (`frontend/`, `app/main.py`)
Redesigns the user experience into a multi-tab clinical workstation:
- **Chat**: Double-mode (Patient/Clinical) assistant with image attachment, voice mic recording, and text-to-speech feedback.
- **Graph**: Interactive form to query the NetworkX graph with live statistics and a visual node network rendering.
- **Tumor Board**: Sandbox patient profile builder (symptoms, drugs, stage, NGS panel) displaying cooperative agent cards.
- **Federated Console**: Control terminal to run multi-round distributed training simulations.

---

## 🔧 Deployment Configuration Guidelines

### Vercel Deployment (Frontend Static Files)
When setting up Vercel, use the following options:
* **Root Directory**: Set to `frontend` (not `./`). This tells Vercel that `index.html` is located inside the frontend subfolder.
* **Framework Preset**: Change from `FastAPI` to `Other` (or `None`). This prevents Vercel from trying to run python scripts as serverless functions.
* **API Redirection**: The javascript calls the hosted Render domain (`https://cancer-awareness-and-healthcare-chatbot-b7za.onrender.com`) directly.

### Render Deployment (FastAPI Python Backend)
* **Build Command**: `pip install -r requirements.txt`
* **Start Command**: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
* **Environment Variables**: Make sure `GROQ_API_KEY` is set in the Render Dashboard Environment settings.

---

## 🧪 Local Test Verification

You can verify the backend API locally at any time using:
```bash
# Run the local FastAPI server
python -m uvicorn app.main:app --port 8000

# Execute the 38-unit evaluation suite
python -m app.evaluation
```
All unit tests verify data traversal, triage urgency limits, visual diagnostic routing, and agent collaboration patterns.

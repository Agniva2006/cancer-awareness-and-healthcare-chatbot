# 🧬 OncoGraph AI (v4.0 Enterprise) — Clinical Cancer Intelligence Platform

An enterprise-grade, multi-modal clinical decision support workstation designed for oncologists, molecular pathologists, and clinical trials networks. The platform integrates a relational **Knowledge Graph Engine**, a **Virtual Tumor Board Swarm**, **Federated Learning Simulations**, and a **DICOM/Pathology Visual Diagnostic Engine** into a stunning, responsive, glassmorphism-styled workspace.

![OncoGraph AI Dashboard](frontend/images/general.png)

---

## 🌐 Live Deployments

* **Enterprise Client Dashboard (Vercel):** [https://frontend-iota-woad-64.vercel.app](https://frontend-iota-woad-64.vercel.app)
* **Clinical Intelligence API (Render):** [https://cancer-awareness-and-healthcare-chatbot-b7za.onrender.com/docs](https://cancer-awareness-and-healthcare-chatbot-b7za.onrender.com/docs)

---

## 🏛️ Platform Architecture

OncoGraph AI uses a decoupled client-server architecture built on FastAPI (API backend) and static HTML/CSS/JS (Vercel frontend client).

```
[ Enterprise Client Dashboard (Vercel) ] 
                 │
                 ▼ (REST API Calls - CORS Enabled)
[ Clinical Intelligence Platform API (Render) ]
   ├── 🕸️ Knowledge Graph Engine (NetworkX relational graph traversal)
   ├── 🤖 Multi-Agent Tumor Board (Triage, Genomic, Trial, Toxicology)
   ├── 🏥 Federated Learning simulation (Proportional FedAvg server)
   └── 🖼️ DICOM / Dermoscopy / Histology Visual Diagnostic Engine
```

---

## 🚀 Key Modules & Capabilities

### 1. Multi-Modal Knowledge Graph Engine (`app/graph_engine.py`)
* Uses **NetworkX** to map relationships between 50+ clinical oncological entities: mutations, FDA-approved targeted therapies, chemotherapy protocols, toxicities, stages, and emergencies.
* Supports **shortest-path reasoning** (e.g. tracing logic from a mutation node to a therapeutic outcome) and comprehensive patient profiling.
* Exports structure dynamically for D3.js/canvas network visualization.

### 2. Multi-Agent Oncological Swarm (`app/agents/tumor_board.py`)
* Simulates a multidisciplinary tumor board (MDT) where four specialized agents collaborate to create a case consensus:
  * **Triage Agent**: Identifies medical urgency (RED/YELLOW) and alerts for acute syndromes (e.g. Febrile Neutropenia).
  * **Genomic Agent**: Extracts free-text biomarker mentions and maps them to FDA targeted therapies via the graph.
  * **Trial Matcher Agent**: Evaluates patient biomarkers against active clinical registries (NCT trials).
  * **Toxicology Agent**: Detects high-risk CYP3A4 inhibitors/inducers (e.g. Ketoconazole interactions) and toxicities.

### 3. Federated Learning Simulation (`federated/hospital_node.py`)
* Simulates training a global classification model across 3 hospital nodes:
  * **Hospital Alpha (Memorial Cancer Center)**: Lung cancer focus (4,200 samples).
  * **Hospital Beta (University Health System)**: Breast cancer focus (3,800 samples).
  * **Hospital Gamma (General Research Hospital)**: Colorectal focus (2,900 samples).
* Executes a privacy-preserving **Federated Averaging (FedAvg)** weight aggregation loop where only model weight gradients leave the hospital perimeters, leaving patient PHI local.

### 4. DICOM & Pathology Visual Diagnostic Engine (`app/dicom_engine.py`)
* Parses DICOM radiology image headers to extract scan modality and slice details.
* Implements dermoscopy scoring using the **ABCDE melanoma criteria** (Asymmetry, Border, Color, Diameter, Evolving) for suspicious skin lesions.
* Evaluates pathology staining profiles (H&E / IHC) for nuclear pleomorphism and tumor-infiltrating lymphocyte counts.

---

## 📂 Project Structure

```text
cancer-awareness-and-healthcare-chatbot/
├── app/
│   ├── agents/
│   │   ├── __init__.py
│   │   └── tumor_board.py    # Multi-Agent orchestrator & specialists
│   ├── dicom_engine.py        # Visual analysis (DICOM, ABCDE, Stains)
│   ├── evaluation.py          # 38-unit testing verification suite
│   ├── graph_engine.py        # NetworkX clinical knowledge graph
│   ├── main.py                # FastAPI endpoints & static mount
│   ├── model.py               # Groq LLM integration
│   ├── prompts.py             # Prompt engineering templates
│   ├── rag.py                 # Cosine similarity text retrieval
│   └── safety.py              # Clinical guardrails & urgency limits
├── data/
│   └── clinical_oncology_kb.json # Structured NCCN/WHO guideline articles
├── federated/
│   └── hospital_node.py       # Simulated hospital nodes & FedAvg server
├── frontend/
│   ├── index.html             # Dashboard template with active panels
│   ├── style.css              # Custom CSS variables, tabs & dashboard cards
│   ├── script.js              # State machine, graphs & REST client
│   └── images/                # Medical illustrations
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation
```

---

## 🔧 Local Development & Running

### 1️⃣ Setup & Installation
```bash
# Clone the repository
git clone https://github.com/Agniva2006/cancer-awareness-and-healthcare-chatbot.git
cd cancer-awareness-and-healthcare-chatbot

# Install python dependencies
pip install -r requirements.txt
```

### 2️⃣ Running the Server
```bash
# Set your Groq API Key (Windows PowerShell example)
$env:GROQ_API_KEY="your_api_key_here"

# Run FastAPI backend locally
python -m uvicorn app.main:app --port 8000
```
* **API Documentation**: Available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Frontend Setup**: Open `frontend/index.html` in your browser. Ensure `API_URL` at the top of `frontend/script.js` points to `http://127.0.0.1:8000` when running locally.

### 3️⃣ Running the Testing Suite
Execute the 38-unit clinical evaluation tests to verify graph traversing, agents, image routing, and federated aggregate status:
```bash
python -m app.evaluation
```

---

## 🔬 Tech Stack

* **Frontend**: HTML5, Vanilla CSS3 (Custom Variables, CSS Keyframe Animations), Vanilla JS (Web Speech API, Canvas Rendering, Panel router).
* **Backend**: FastAPI (Python), NetworkX (Graph Reasoning), NumPy (FedAvg calculations), Scikit-Learn (TF-IDF Cosine similarity).
* **Inference**: Groq API Cloud (Llama 3).
* **Deployments**: Vercel (Client Dashboard), Render (FastAPI Server).

---

## ⚠️ Medical Disclaimer

OncoGraph AI is built for **clinical decision support and educational research purposes only**. It does **not** replace the judgment of a primary oncologist or professional clinical diagnosis.

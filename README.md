# 🧬 OncoGraph AI (v4.1 Enterprise) — Clinical Cancer Intelligence Platform

An enterprise-grade, multi-modal clinical decision support workstation designed for oncologists, molecular pathologists, and clinical trials networks. The platform integrates a relational **Knowledge Graph Engine**, a **Virtual Tumor Board Swarm**, **Federated Learning Simulations**, and a **DICOM/Pathology Visual Diagnostic Engine** into a stunning, responsive, glassmorphism-styled workspace.

![OncoGraph AI Dashboard](frontend/images/general.png)

---

## 🌐 Live Deployments

* **Enterprise Client Dashboard (Vercel):** [https://cancer-awareness-and-healthcare-cha.vercel.app/](https://cancer-awareness-and-healthcare-cha.vercel.app/)
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
│   ├── auth.py                # JWT auth, bcrypt, rate-limiting, plan gating ★ NEW
│   ├── dicom_engine.py        # Visual analysis (DICOM, ABCDE, Stains)
│   ├── evaluation.py          # 38-unit testing verification suite
│   ├── graph_engine.py        # NetworkX clinical knowledge graph
│   ├── main.py                # FastAPI endpoints, JWT-protected routes
│   ├── model.py               # Groq LLM integration
│   ├── ml_predictor.py        # Random Forest prognosis model
│   ├── prompts.py             # Prompt engineering templates
│   ├── rag.py                 # Cosine similarity text retrieval
│   ├── safety.py              # Clinical guardrails & urgency limits
│   ├── triage.py              # RED/YELLOW/GREEN clinical triage
│   └── vision.py              # Medical image analysis
├── data/
│   ├── clinical_oncology_kb.json # Structured NCCN/WHO guideline articles
│   └── users_db.json          # User accounts store (bcrypt passwords) ★ UPDATED
├── federated/
│   └── hospital_node.py       # Simulated hospital nodes & FedAvg server
├── frontend/
│   ├── index.html             # Dashboard + Auth/Profile/Subscription modals ★ UPDATED
│   ├── style.css              # Main design system
│   ├── style-auth.css         # Auth modal, profile, subscription, onboarding ★ NEW
│   ├── script.js              # JWT auth flow, plan gating, all panels ★ UPDATED
│   └── images/                # Medical illustrations
├── requirements.txt           # Python dependencies (+ jose, passlib, multipart)
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
* **Backend**: FastAPI (Python), NetworkX (Graph Reasoning), NumPy (FedAvg), Scikit-Learn (TF-IDF), `python-jose` (JWT), `passlib[bcrypt]` (password hashing).
* **Auth**: Stateless JWT Bearer tokens — issued on login, verified on every protected endpoint.
* **Inference**: Groq API Cloud (Llama 3).
* **Deployments**: Vercel (Static frontend), Render (FastAPI server).

---

## 🔐 Authentication & Subscription (v4.1)

### Subscription Plans

| Plan | Price | Daily Quota | Features |
|---|---|---|---|
| **Free** | $0/mo | 10 queries | Chat only |
| **Clinical** | $49/mo | 500 queries | + Knowledge Graph, ML Prognosis, DICOM |
| **Enterprise** | $199/mo | Unlimited | + Tumor Board, Federated Learning, all features |

### Demo Account (pre-seeded)

| Field | Value |
|---|---|
| **Username** | `demo` |
| **Password** | `oncograph2024` |
| **Plan** | Enterprise (all features unlocked) |

Register your own account at the login screen — all new accounts start on the **Free** plan and can be upgraded in-app.

---

## ☁️ Deployment Configuration

### Render (Backend API)

> **Critical:** Render's free tier has an ephemeral filesystem. Set the `ONCOGRAPH_SECRET_KEY` environment variable in your Render service dashboard to keep JWT tokens valid across restarts/redeploys.

**Required Environment Variables on Render:**

| Variable | Description | Example |
|---|---|---|
| `GROQ_API_KEY` | Your Groq LLM API key | `gsk_...` |
| `ONCOGRAPH_SECRET_KEY` | Stable 64-char hex string for JWT signing | `openssl rand -hex 32` |

**Steps:**
1. Go to your Render service → **Environment** tab
2. Add `ONCOGRAPH_SECRET_KEY` = output of `openssl rand -hex 32` (or any strong secret)
3. Add `GROQ_API_KEY` = your key from [console.groq.com](https://console.groq.com)
4. Deploy — tokens will now survive restarts

### Vercel (Frontend)

No configuration needed. Push to GitHub — Vercel auto-deploys `frontend/` as a static site. Ensure the new `frontend/style-auth.css` is committed.

### Commit Checklist (v4.1 upgrade)

```bash
git add app/auth.py app/main.py requirements.txt
git add frontend/index.html frontend/script.js frontend/style-auth.css
git add data/users_db.json
git commit -m "feat: JWT auth, subscription tiers, profile, onboarding (v4.1)"
git push
```

---

## ⚠️ Medical Disclaimer

OncoGraph AI is built for **clinical decision support and educational research purposes only**. It does **not** replace the judgment of a primary oncologist or professional clinical diagnosis.

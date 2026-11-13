# 🎗️ Cancer Awareness & Healthcare Chatbot

A production-structured web chatbot that answers general cancer awareness, prevention, screening, and care questions. It uses a local knowledge dataset (`data/`) with TF-IDF retrieval (RAG) and a Groq LLM backed by a multi-model fallback chain, plus a safety guardrail that blocks medical-decision queries.

**🚀 Live demo:** Frontend on Vercel · Backend API on Render

> ⚠️ **Medical disclaimer:** This chatbot provides general educational information only. It is not a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider.

---

## ✨ Features

- **RAG pipeline** — TF-IDF retrieval over a curated cancer knowledge base, with the top matches fed as grounded context to the LLM.
- **Multi-model fallback** — if one Groq model times out or fails, the next in the chain takes over automatically.
- **Safety guardrail** — validates input (query length ≤ 1000 chars, mode ∈ {patient, clinical}) and refuses unsafe or medical-decision questions.
- **Triage & confidence** — responses include suggested urgency triage, cited sources, and a confidence score.
- **Rich chat UI** — vanilla JS single-page app with chat history (localStorage), search & export, dark/light theme, voice input (Web Speech API), text-to-speech, and session management.
- **REST API** — versioned FastAPI layer with health checks and structured logging.

## 🏗️ Project Structure

```
├── app/
│   ├── main.py               # App factory entrypoint (uvicorn app.main:app)
│   ├── api/v1/               # Versioned API layer
│   │   ├── router.py         # Aggregates endpoint modules
│   │   └── endpoints/        # health.py, chat.py
│   ├── core/                 # Config, logging, constants
│   ├── schemas/              # Pydantic request/response models
│   ├── services/             # Business logic: rag, model, prompts, safety, triage
│   └── utils/                # Timing, text helpers
├── data/                     # Knowledge base (cancer_data.json, clinical_oncology_kb.json)
├── frontend/                 # Vanilla HTML/CSS/JS SPA
├── tests/                    # pytest suite (endpoints, safety, triage, RAG)
├── scripts/                  # Dev helpers (kb_stats.py, seed_knowledge.py, smoke_test.py)
├── requirements.txt          # Runtime + dev dependencies
├── pytest.ini / setup.cfg    # Test and lint config
├── Dockerfile / Procfile / render.yaml  # Deployment
└── .env.example              # Template for secrets
```

## 🌐 Deployment

The project is deployed with a split architecture — static frontend on **Vercel**, FastAPI backend on **Render**:

### Backend — Render

Deploys from `render.yaml` (Python environment, free tier, Oregon region):

```yaml
buildCommand: pip install -r requirements.txt
startCommand:  uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set `GROQ_API_KEY` in the Render dashboard under **Environment** (it is marked `sync: false`, so it is never committed). Also set `ALLOWED_ORIGINS` to include your Vercel frontend URL so CORS allows the browser to call the API.

### Frontend — Vercel

The `frontend/` folder is served as a static site. `frontend/script.js` auto-detects the environment:

```js
const isLocal = window.location.hostname === 'localhost' || ...;
const API_URL = isLocal
    ? "http://127.0.0.1:8000"
    : "https://cancer-awareness-and-healthcare-chatbot-n2wy.onrender.com";
```

Locally it hits `127.0.0.1:8000`; on Vercel it points at the Render backend. To point it at a different deployment, change the `API_URL` fallback.

### Docker (alternative)

```bash
docker build -t cancer-chatbot .
docker run -p 8000:8000 -e GROQ_API_KEY=... cancer-chatbot
```

### Local development

1. Copy `.env.example` to `.env` and add your Groq API key (get one at [console.groq.com/keys](https://console.groq.com/keys)).
2. Install dependencies and run:

```powershell
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000/frontend/` (served by the API), or open `frontend/index.html` directly, or serve the frontend statically (e.g. VS Code Live Server) while the API runs on port 8000.

## ⚙️ Configuration

All settings are loaded from environment variables (see `.env.example`):

| Variable | Purpose |
| --- | --- |
| `GROQ_API_KEY` | Required — Groq API key |
| `ALLOWED_ORIGINS` | CORS allowlist (comma-separated) |
| `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT_SECONDS` | Generation tuning |
| `RAG_TOP_K`, `RAG_SCORE_THRESHOLD`, `RAG_FINAL_TOP_N` | Retrieval tuning |
| `LOG_FORMAT`, `ENVIRONMENT` | `json` / `production` on hosting platforms |

## 🔌 API

Interactive docs are auto-generated at `/docs` (Swagger UI).

| Method | Path      | Description                                  |
|--------|-----------|----------------------------------------------|
| GET    | `/`       | Service info                                 |
| GET    | `/health` | Liveness probe                               |
| POST   | `/ask`    | Ask a question; returns answer, sources, triage, confidence, latency |

Example:

```bash
curl -X POST https://<your-render-app>.onrender.com/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What are early signs of breast cancer?", "mode": "patient"}'
```

## 🧪 Tests

```powershell
pytest
```

## 🔒 Security Notes

- The `.env` file contains secrets and is git-ignored — never commit it. If a key was ever committed, revoke it and generate a new one.
- Secrets are injected via environment variables at runtime (Render dashboard); the Dockerfile copies only source code.
- Requests are validated (query length ≤ 1000, mode ∈ {patient, clinical}) and unsafe/medical-decision queries are blocked by the safety guardrail.

## 📄 License

Educational/personal project — see repository for licensing details.

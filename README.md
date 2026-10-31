# Cancer Awareness Chatbot

A production-structured web chatbot that answers general cancer awareness questions using a local knowledge dataset (`data/`), TF-IDF retrieval (RAG), and a Groq LLM with a multi-model fallback chain.

## Project Structure

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
├── scripts/                  # Dev helpers (kb_stats.py)
├── requirements.txt          # Runtime + dev dependencies
├── pytest.ini / setup.cfg    # Test and lint config
├── Dockerfile / Procfile / render.yaml  # Deployment
└── .env.example              # Template for secrets
```

## Setup

1. Copy `.env.example` to `.env` and add your Groq API key (get one at [console.groq.com/keys](https://console.groq.com/keys)).
2. Install dependencies and run:

```powershell
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000/frontend/` (served by the API) or open `frontend/index.html` directly. The API provides `/health` and `/ask`.

## Tests

```powershell
pytest
```

## Configuration

All settings are loaded from environment variables (see `.env.example`):

- `GROQ_API_KEY` — required, Groq API key
- `ALLOWED_ORIGINS` — CORS allowlist (comma-separated)
- `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT_SECONDS` — generation tuning
- `RAG_TOP_K`, `RAG_SCORE_THRESHOLD`, `RAG_FINAL_TOP_N` — retrieval tuning

## Security notes

- The `.env` file contains secrets and is git-ignored — never commit it. If a key was ever committed, revoke it and generate a new one.
- The Dockerfile copies only source code (`app/`, `data/`, `frontend/`, `tests/`) — secrets must be injected via environment variables at runtime.
- Requests are validated (query length ≤ 1000, mode ∈ {patient, clinical}) and unsafe/medical-decision queries are blocked by the safety guardrail.

## API

| Method | Path      | Description                                  |
|--------|-----------|----------------------------------------------|
| GET    | `/`       | Service info                                 |
| GET    | `/health` | Liveness probe                               |
| POST   | `/ask`    | Ask a question; returns answer, sources, triage, confidence, latency |

# Cancer Awareness Chatbot

A web chatbot that answers general cancer awareness questions using the local knowledge dataset in `data/`.

## Setup

1. Copy `.env.example` to `.env` and add your Groq API key (get one at [console.groq.com/keys](https://console.groq.com/keys)).
2. Install dependencies and run:

```powershell
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `frontend/index.html` in a browser, or visit `http://localhost:8000/frontend/` (served by the API). The API provides `/health` and `/ask`.

## Security notes

- The `.env` file contains secrets and is git-ignored — never commit it. If a key was ever committed, revoke it and generate a new one.
- Allowed CORS origins can be configured via the `ALLOWED_ORIGINS` environment variable (comma-separated).

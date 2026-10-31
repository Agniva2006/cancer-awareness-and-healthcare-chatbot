# Cancer Awareness Chatbot

A web chatbot that answers general cancer awareness questions using the local knowledge dataset in `data/`.

## Run locally

```powershell
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `frontend/index.html` in a browser or visit the frontend deployment. The API provides `/health` and `/ask`.

The cancer knowledge files and database-related Python integrations are retained in the repository.

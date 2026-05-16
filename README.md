# 🧬 Cancer AI Assistant 2.0 (RAG + LLM + Advanced UI)

An intelligent, AI-powered cancer information companion built using **Retrieval-Augmented Generation (RAG)** and **Groq (Llama 3)**. The project features a robust FastAPI backend combined with a state-of-the-art, glassmorphism-styled frontend offering rich accessibility and media features.

![Cancer AI Assistant](frontend/images/general.png)

---

## 🌐 Live Demo

- **Frontend (Web App):** [https://frontend-iota-woad-64.vercel.app](https://frontend-iota-woad-64.vercel.app)
- **Backend API:** [https://cancer-awareness-and-healthcare-chatbot-b7za.onrender.com/docs](https://cancer-awareness-and-healthcare-chatbot-b7za.onrender.com/docs)

---

## 🚀 Key Features

### 💻 Frontend (Top 1% UI/UX Experience)
- **Voice Capabilities:** Built-in Speech-to-Text (🎤) for asking questions and Text-to-Speech (🔊) auto-read for answers.
- **Smart Topic Illustrations:** Automatically detects the medical topic (Lung, Breast, Chemo, Radiation, etc.) from context and displays a beautiful infographic.
- **Image Uploads & Lightbox:** Attach visual context to queries and view images in a full-screen, zoomable lightbox modal.
- **Session Management:** Stores chat history persistently in the browser (`localStorage`). Start new chats, search history, or clear logs.
- **Export Chat:** Download your conversation history as a formatted `.txt` file.
- **Stunning UI:** Features a dynamic particle background, dark/light theme toggles, smooth micro-animations, glassmorphism panels, and responsive mobile design.
- **Real-time Analytics:** Tracks session metrics including average confidence and response latency.

### ⚙️ Backend (RAG Pipeline)
- **RAG-based Retrieval:** Uses TF-IDF + cosine similarity to fetch the most relevant medical context from a curated dataset.
- **Groq LLM Integration:** Powered by Llama-3-70b for extremely fast and high-quality inference.
- **Safety First Guardrails:** A heuristic safety layer intercepts queries attempting to seek direct diagnosis or prescriptions, gracefully redirecting users to medical professionals.
- **Structured API:** Built on FastAPI for high performance and clean JSON responses with latency/confidence metrics.
- **CORS Enabled:** Fully configured to accept cross-origin requests from the deployed frontend.

---

## 📂 Project Structure

```text
cancer-ai-assistant/
├── app/
│   ├── main.py        # FastAPI app & CORS setup
│   ├── rag.py         # TF-IDF Retrieval system
│   ├── model.py       # Groq LLM integration & fallback handling
│   ├── prompts.py     # Prompt engineering
│   └── safety.py      # Medical safety guardrails
│
├── data/
│   └── cancer_data.json # RAG Knowledge Base
│
├── frontend/
│   ├── index.html     # Semantic HTML layout
│   ├── style.css      # Custom CSS, Glassmorphism, Animations
│   ├── script.js      # API integration, Voice, LocalStorage logic
│   └── images/        # Topic-specific medical illustrations
│
├── requirements.txt   # Python dependencies
└── README.md          # Project documentation
```

---

## ⚙️ Local Development Setup

### 1️⃣ Clone the Repository
```bash
git clone <your-repo-link>
cd cancer-ai-assistant
```

### 2️⃣ Backend Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set your Groq API Key (Windows PowerShell)
setx GROQ_API_KEY "your_api_key_here"

# Run the FastAPI server
uvicorn app.main:app --reload
```
The backend will run at `http://127.0.0.1:8000`. API docs are available at `http://127.0.0.1:8000/docs`.

### 3️⃣ Frontend Setup
1. Open the `frontend/script.js` file.
2. For local testing, ensure the `API_URL` points to your local server:
   ```javascript
   const API_URL = "http://127.0.0.1:8000/ask";
   ```
3. Open `frontend/index.html` in your browser (preferably using an extension like VS Code Live Server).

---

## ⚠️ Disclaimer

This system is for **educational and informational purposes only**.
It does **not provide medical diagnosis, prescriptions, or treatment advice**.
Always consult a qualified healthcare professional or oncologist for medical decisions.

---

## 🔥 Tech Stack

- **Frontend:** Vanilla HTML5, CSS3 (Custom Properties, Glassmorphism, CSS Animations), Vanilla JavaScript (Web Speech API, DOM manipulation).
- **Backend:** FastAPI, Python, Scikit-learn (TF-IDF).
- **AI/LLM:** Groq API (Llama 3).
- **Deployment:** Vercel (Frontend), Render (Backend).

---

## 👨‍💻 Author

Built as an AI/ML production-level project with a premium top-tier web interface.

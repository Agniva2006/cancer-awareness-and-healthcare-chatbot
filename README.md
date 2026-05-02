# 🧬 Cancer AI Assistant (RAG + LLM)

An AI-powered cancer information assistant built using **Retrieval-Augmented Generation (RAG)** and **LLM (Groq - Llama 3)** to provide safe, structured, and reliable patient-focused responses.

---

## 🚀 Features

* 🔍 **RAG-based Retrieval**

  * TF-IDF + cosine similarity
  * Context-aware responses

* 🧠 **LLM Integration**

  * Powered by Groq (Llama 3)
  * Fast and high-quality inference

* 🛡️ **Safety Layer**

  * Detects unsafe medical queries
  * Prevents diagnosis or prescriptions

* 📦 **Structured API**

  * Built with FastAPI
  * Clean JSON responses

* 📊 **Logging + Debugging**

  * Query + sources + response tracking

---

## 🧠 Architecture

User Query → Safety Check → RAG Retrieval → Re-ranking → Prompt Building → LLM (Groq) → Response

---

## 📂 Project Structure

```
app/
  main.py        # FastAPI app
  rag.py         # Retrieval system
  model.py       # Groq LLM integration
  prompts.py     # Prompt engineering
  safety.py      # Safety guardrails

data/
  cancer_data.json

requirements.txt
README.md
```

---

## ⚙️ Setup Instructions

### 1️⃣ Clone repo

```
git clone <your-repo-link>
cd cancer-ai-assistant
```

---

### 2️⃣ Install dependencies

```
pip install -r requirements.txt
```

---

### 3️⃣ Set environment variable

```
GROQ_API_KEY=your_api_key_here
```

(Windows PowerShell)

```
setx GROQ_API_KEY "your_api_key_here"
```

---

### 4️⃣ Run the server

```
uvicorn app.main:app --reload
```

---

### 5️⃣ Open API docs

```
http://127.0.0.1:8000/docs
```

---

## 🧪 Example Query

```
{
  "query": "What are symptoms of lung cancer?"
}
```

---

## ⚠️ Disclaimer

This system is for **educational and informational purposes only**.
It does **not provide medical diagnosis or treatment advice**.
Always consult a qualified healthcare professional.

---

## 🔥 Tech Stack

* FastAPI
* Scikit-learn (TF-IDF)
* Groq API (Llama 3)
* Python

---

## 🎯 Key Highlights

* End-to-end AI system (RAG + LLM)
* Safety-aware healthcare chatbot
* Production-ready API design
* Deployable architecture

---

## 🚀 Future Improvements

* Better embeddings (BGE / OpenAI)
* UI (Streamlit / React)
* Logging + monitoring
* Fine-tuning (LoRA)

---

## 👨‍💻 Author

Built as an AI/ML production-level project.

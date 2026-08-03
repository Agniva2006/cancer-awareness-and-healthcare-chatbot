# OncoGraph AI (v4.0) — Technical & HR Interview Presentation Guide

This guide is your ultimate cheat-sheet to present **OncoGraph AI** in job interviews. It is written using **simple, non-technical analogies** so you can easily explain complex concepts to HR recruiters, while keeping **deep technical breakdowns** to impress senior engineering leads.

---

## ⚡ The 30-Second Elevator Pitch (What is this project?)
> *"Most medical AI projects are just simple chatbots that guess answers and make mistakes. **OncoGraph AI** is an advanced, double-sided clinical dashboard designed for doctors and patients. Instead of just chatting, it uses a structured **Knowledge Graph** to prevent medical errors, runs **4 specialized AI agents** that collaborate like a real panel of doctors, and uses **Federated Learning** to simulate training AI across different hospitals while keeping private patient records 100% safe and compliant with healthcare privacy laws."*

---

## 🗺️ How to Explain the 4 Core Features using Simple Analogies

When talking to HR or recruiters who don't know code or oncology, use these exact analogies:

| Technical Feature | Simple Analogy | Easy Explanation |
| :--- | :--- | :--- |
| **Knowledge Graph** (`NetworkX`) | **A Subway Map / Family Tree** | Instead of searching through long text documents, we connect medical concepts (Mutations, Drugs, Side Effects) like a map. If a patient is at Station A (Mutation), the AI follows the track to Station B (Drug) and alerts them if they hit a dead-end or danger zone (Side Effect). |
| **Multi-Agent Swarm** (`tumor_board.py`) | **A Medical Group Chat** | Instead of one AI trying to do everything, we spawn a team of 4 AI specialists: a **Genomics Expert**, a **Drug Side-Effect Expert**, a **Clinical Trials Scout**, and an **Emergency Responder**. They analyze the patient's data together and agree on a consensus treatment report. |
| **Federated Learning** (`hospital_node.py`) | **Classrooms Sharing Notes** | Three hospitals want to train an AI model but cannot share private patient records due to privacy laws. It's like students in separate classrooms studying for a test. They don't copy each other's private homework; they only share their study guides (model weights) to help everyone get smarter. |
| **DICOM Vision Engine** (`dicom_engine.py`) | **A Digital Sorting Office** | A doctor uploads a medical file (like a CT scan or a skin lesion photo). The AI automatically reads the file type, formats it, and routes it to the correct specialist tool for score extraction. |

---

## 🎬 Live Demo Script (What to say and do in a live interview)

Follow this exact guide during a screen-share:

### Step 1: Open the App and Show the Triage Warning
* **Action**: Open the dashboard, make sure you are in the **Chat** tab, and click the chip: **"Febrile Neutropenia Emergency"**.
* **What to say**: 
  > *"First, let's look at the chat. I'll click this suggestion for a high-risk symptom: a chemo patient with a fever. Notice that the AI immediately flags a bright red **EMERGENCY TRIAGE ALERT**. In oncology, a chemo patient with a fever is a life-threatening emergency called Febrile Neutropenia. Instead of giving generic chatbot answers, the AI instantly warns the user to seek immediate emergency care and provides the exact medical billing code (ICD-10 D70.1) for doctors."*

### Step 2: Show the Knowledge Graph
* **Action**: Click the **Graph** tab in the sidebar. Type `EGFR_EX19DEL` into the input box and click **Traverse Graph**.
* **What to say**:
  > *"Next, let's look at the Knowledge Graph. If we query the mutation `EGFR_EX19DEL`, the system traverses a structured database of connected nodes. It doesn't guess the treatment; it follows a hard-coded path to tell us that this mutation responds to the targeted therapy **Osimertinib** with NCCN Category 1 evidence. This eliminates the risk of AI hallucination, which is vital for patient safety."*

### Step 3: Run the Virtual Tumor Board
* **Action**: Click the **Tumor Board** tab. Click the **"NSCLC + EGFR L858R"** preset chip, then click the green **Run Tumor Board Analysis** button.
* **What to say**:
  > *"Now, let's simulate a Multidisciplinary Tumor Board—which is a meeting where different medical specialists review a case. When I run this, 4 specialized AI agents analyze the patient profile. The Genomics Agent matches the treatment, the Trial Matcher checks if they are eligible for active trials, and the Toxicology Agent flags if the patient's other medications (like Ketoconazole) will interfere with their cancer drugs. They compile their findings into a single structured report in under two seconds."*

### Step 4: Show the Federated Learning Simulation
* **Action**: Click the **Federated** tab. Click the orange **Launch Federated Training** button.
* **What to say**:
  > *"Finally, here is the Federated Learning module. We are simulating a network of 3 hospitals: Memorial Cancer Center, University Health System, and General Research Hospital. Because of HIPAA privacy laws, these hospitals cannot share patient scans. When I click train, each hospital trains the AI model locally on its own computer. They only share the mathematical updates (weights) with our central server. The loss rates go down, meaning the AI gets smarter, while the private patient data remains 100% safe inside each hospital's database."*

---

## 💬 Top 5 Interview Questions & Easy-to-Understand Answers

Use these answers to handle both HR and technical interviewers:

### Q1: Why didn't you just build a standard chat bot? What makes this special?
* **Answer (Easy & HR-friendly)**: *"Standard chatbots are dangerous in medicine because they guess words based on probability, which leads to hallucinations (made-up facts). By building a Knowledge Graph, we created a deterministic system—the AI is forced to follow exact, verified NCCN guidelines. It is the difference between an AI guessing a medical prescription versus looking it up on an official, structured medical map."*

### Q2: What is the benefit of a "Multi-Agent" system over a single LLM prompt?
* **Answer (Easy & HR-friendly)**: *"If you ask a single AI model to diagnose, check drug side effects, find clinical trials, and check emergency levels all in one prompt, it gets overwhelmed and makes mistakes. By breaking it into 4 specialist agents, each agent has one simple job. It's like running a medical clinic: you don't have the surgeon do the pharmacy work; you hire a separate pharmacist, oncologist, and emergency nurse to work together."*

### Q3: How does your Federated Learning aggregation actually work?
* **Answer (Technical)**: *"We implement the **Federated Averaging (FedAvg)** algorithm. Each simulated hospital client (HospitalNode) initializes local weights. During a training round, the client trains the model on its local data partition and computes weight updates. These updates are sent to the central server (FederatedServer), which computes a weighted average of the weights (proportional to each hospital's sample size) and redistributes the new global weights back to the clients. This preserves data privacy since raw inputs never leave the client's local context."*

### Q4: Why did you use NetworkX for the Knowledge Graph?
* **Answer (Technical)**: *"NetworkX is a powerful Python library for studying graphs and networks. It allows us to create a directed graph in memory, perform fast topological sorting, search for connected components, and find the shortest path of relationships between a biomarker and a clinical treatment. It is lightweight, fast, and does not require the overhead of hosting a separate database service like Neo4j."*

### Q5: What is the medical value of the Toxicology Agent?
* **Answer (Easy & HR-friendly)**: *"In cancer treatment, patients often take multiple medications. For example, some common medications block the enzymes (like CYP3A4) that break down cancer drugs. If a patient is taking Ketoconazole, their body can't clear the cancer drug Osimertinib, leading to dangerous toxicity levels. The Toxicology Agent automatically checks for these chemical drug-drug interactions, saving the oncologist from cross-referencing massive drug databases manually."*

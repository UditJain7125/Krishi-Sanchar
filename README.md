# 🌾 KrishiSanchar (कृषि संचार)
### *Next-Generation AI & ML-Powered Smart Agriculture Ecosystem*

[![Live Demo](https://img.shields.io/badge/Live_Demo-GitHub_Pages-2ea44f?style=for-the-badge&logo=github)](https://uditjain7125.github.io)
[![Backend Status](https://img.shields.io/badge/Backend-Render_Cloud-46E3B7?style=for-the-badge&logo=render)](https://render.com)
[![Database](https://img.shields.io/badge/Database-Neon_PostgreSQL-00E599?style=for-the-badge&logo=postgresql)](https://neon.tech)
[![AI Engine](https://img.shields.io/badge/AI-Google_Gemini-8E75C2?style=for-the-badge&logo=google)](https://deepmind.google/technologies/gemini/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python)](https://python.org)

---

## 📖 Overview

**KrishiSanchar** is a full-stack, cloud-native smart agriculture platform engineered to empower farmers with precision agriculture tools, artificial intelligence, and machine learning. 

From diagnosing crop leaf diseases and recommending optimal crops and fertilizers, to real-time mandi price analysis, hyperlocal weather advisory, and yield forecasting, KrishiSanchar provides an end-to-end digital dashboard tailored for modern Indian agriculture.

---

## 🏛️ System Architecture

KrishiSanchar follows a **decoupled microservices architecture**. The client application communicates over HTTPS with independent FastAPI microservices deployed on the cloud, backed by Google Gemini Generative AI, trained ML/DL models, and a centralized serverless PostgreSQL database.

```mermaid
flowchart TB
    subgraph ClientLayer["🖥️ Client Layer (Frontend)"]
        UI["Web Dashboard & Mobile View<br/>(HTML5 / Modern CSS / Vanilla JS)"]
        Host["GitHub Pages Hosting<br/>(https://uditjain7125.github.io)"]
        UI --- Host
    end

    subgraph APIGateway["🌐 API Communication Layer"]
        CORS["CORS & Secure REST Endpoints<br/>(JSON Payloads / Form-Data)"]
    end

    subgraph Microservices["⚙️ Backend Microservices (FastAPI on Render)"]
        AUTH["Auth & Profile Service<br/>(Port: 8007)"]
        DISEASE["Plant Disease Detection<br/>(Port: 8006)"]
        CROP["Crop Recommendation<br/>(Port: 8000)"]
        FERT["Fertilizer Recommendation<br/>(Port: 8001)"]
        YIELD["Yield Prediction<br/>(Port: 8002)"]
        MARKET["Market Analysis<br/>(Port: 8003)"]
        WEATHER["Weather Service<br/>(Port: 8004)"]
        AI_BOT["AI Farming Assistant<br/>(Port: 8005)"]
    end

    subgraph IntelligenceLayer["🧠 AI & ML Engines"]
        GEMINI["Google Gemini 3.1 Flash<br/>(Agricultural LLM Advisory)"]
        DL_MODEL["Deep Learning CNN / TFLite<br/>(Plant Disease Classifier)"]
        ML_MODELS["Scikit-Learn Models<br/>(RandomForest / XGBoost / Encoders)"]
    end

    subgraph DataStorage["🗄️ Persistence & Cloud Data"]
        NEON[("Neon Serverless PostgreSQL<br/>• Farmer Profiles<br/>• Calculation History<br/>• Cached Mandi Prices")]
        GOV_API["AGMARKNET / data.gov.in<br/>(National Mandi Price Feeds)"]
        GHA["GitHub Actions<br/>(Daily Cron Fetch & Sync)"]
    end

    %% Connections
    UI ==> CORS
    CORS ==> AUTH
    CORS ==> DISEASE
    CORS ==> CROP
    CORS ==> FERT
    CORS ==> YIELD
    CORS ==> MARKET
    CORS ==> WEATHER
    CORS ==> AI_BOT

    AUTH <--> NEON
    MARKET <--> NEON
    GHA -->|Daily Price Pull| GOV_API
    GHA -->|Batch Upsert| NEON

    DISEASE --> DL_MODEL
    CROP --> ML_MODELS
    FERT --> ML_MODELS
    YIELD --> ML_MODELS
    WEATHER --> GEMINI
    MARKET --> GEMINI
    AI_BOT --> GEMINI
```

---

## 🔄 End-to-End User Interaction Flow Chart

```mermaid
sequenceDiagram
    autonumber
    actor Farmer as 👨‍🌾 Farmer / User
    participant Frontend as 💻 KrishiSanchar UI
    participant Auth as 🔐 Auth Service (8007)
    participant Service as ⚡ Specialized Microservice
    participant AI_ML as 🧠 ML Model / Gemini AI
    participant DB as 🐘 Neon PostgreSQL

    Farmer->>Frontend: Register or Login with Mobile / Email
    Frontend->>Auth: POST /login (credentials)
    Auth->>DB: Verify Bcrypt Hash & Fetch Profile
    DB-->>Auth: Farmer Profile Record
    Auth-->>Frontend: JWT Token + Farmer Details
    Frontend->>Auth: GET /history (load previous logs)
    Auth->>DB: Fetch farmer_id history
    DB-->>Auth: Activity records
    Auth-->>Frontend: Render Dashboard & Saved History

    Note over Farmer,Frontend: Farmer Selects a Service (e.g. Disease Detection / Market Prices)

    Farmer->>Frontend: Submits Inputs (Image, Soil NPK, Crop Name, etc.)
    Frontend->>Service: REST Request with payload
    alt Machine Learning / Deep Learning
        Service->>AI_ML: Feed normalized tensor / feature vector
        AI_ML-->>Service: Class prediction, confidence score & metrics
    else Generative AI Advisory
        Service->>AI_ML: Contextualized prompt with agricultural parameters
        AI_ML-->>Service: Tailored agronomic recommendations
    else Market Mandi Prices
        Service->>DB: Query cached Mandi prices for commodity
        DB-->>Service: Price records across mandis
        Service->>AI_ML: Generate best selling strategy
        AI_ML-->>Service: Mandi price range + Actionable advice
    end

    Service-->>Frontend: Structured JSON response
    Frontend->>Auth: POST /history (Log interaction)
    Auth->>DB: Insert into history_entries
    Frontend-->>Farmer: Visual Results (Charts, Badges, Advice Cards)
```

---

## ✨ Core Features & Microservices

| Service | Port | Description & Tech |
|---|:---:|---|
| **🔐 Authentication & Profile** | `8007` | JWT tokens, Bcrypt password hashing, full farmer profiles (soil type, land area, location), and synchronized calculation history. |
| **🌿 Plant Disease Detection** | `8006` | Deep learning leaf image classification detecting diseases across multiple crops with confidence scores, prevention, and treatment measures. |
| **🌱 Crop Recommendation** | `8000` | Machine Learning model analyzing soil N-P-K levels, temperature, humidity, pH, and rainfall to recommend the highest-yielding crop. |
| **🧪 Fertilizer Recommendation** | `8001` | Suggests precise NPK fertilizer requirements and organic supplements based on soil test parameters and target crops. |
| **📈 Yield Prediction** | `8002` | Regression model using multi-crop encoders, land acreage, fertilizer dosage, and soil conditions to predict yield per acre and total harvest. |
| **📊 Market Mandi Analysis** | `8003` | Real-time commodity mandi prices across Indian states with automated fallback caching in PostgreSQL and Gemini AI selling advice. |
| **⛅ Hyperlocal Weather & Advisory** | `8004` | 5-day meteorological forecasts paired with AI agricultural advisories for sowing, irrigation, and pesticide application. |
| **🤖 AI Farming Assistant** | `8005` | 24/7 conversational agricultural chatbot powered by Google Gemini, capable of answering agronomic and scheme queries in plain language. |

---

## 🛠️ Technology Stack

### **Frontend**
* **HTML5, Modern Responsive CSS3, Vanilla ES6+ JavaScript**
* **Icons & Visuals:** FontAwesome 6, SVG dynamic chart generators
* **Deployment:** GitHub Pages

### **Backend & Microservices**
* **Framework:** FastAPI (Python 3.11) with ASGI Uvicorn servers
* **Authentication:** PyJWT, Bcrypt
* **Networking & Resilience:** Requests, Urllib3 HTTPAdapter with exponential backoff retries, CORS Middleware

### **Artificial Intelligence & Data Science**
* **Generative AI:** Google Gemini (`gemini-3.1-flash-lite`) via `langchain-google-genai`
* **Machine Learning:** Scikit-Learn, Pandas, NumPy, Pickle model pipelines
* **Deep Learning / Vision:** TensorFlow, Keras, Pillow (`PIL`), AI-Edge LiteRT

### **Database & Cloud Storage**
* **Database:** Serverless PostgreSQL via **Neon.tech**
* **ORM:** SQLAlchemy 2.0 with connection pooling (`pool_pre_ping`) and `psycopg2-binary`
* **Schema:** `farmer_profiles`, `history_entries`, `market_prices`

### **DevOps & Automations**
* **Cloud Hosting:** Render Web Services (`render.yaml`)
* **Scheduled Workflows:**
  * `.github/workflows/fetch_market_data.yml` — Daily automated AGMARKNET data synchronization
  * `.github/workflows/keep_alive.yml` — Automated 24/7 Keep-Alive heartbeat for Render free-tier instances
* **Local Multi-Service Orchestrator:** `all.py` (Spawns and monitors all 8 services simultaneously)

---

## 📂 Project Directory Structure

```text
Smart agriculture platform/
│
├── .github/workflows/
│   ├── fetch_market_data.yml     # Automated daily AGMARKNET price fetcher
│   └── keep_alive.yml            # 24/7 keep-alive ping workflow
│
├── auth/
│   ├── auth_service.py           # Authentication & History REST API
│   ├── Database.py               # Shared SQLAlchemy models & DB connection
│   └── requirements.txt          # Auth microservice dependencies
│
├── Crop recommendation/
│   ├── app.py                    # Crop recommendation FastAPI service
│   ├── Crop_Recommendation.pkl   # Trained crop ML model
│   └── requirements.txt
│
├── Fertilizer recommendation/
│   ├── Fertilizer.py             # Fertilizer recommendation service
│   ├── fertilizer.pkl            # Trained fertilizer model
│   └── requirements.txt
│
├── plant disease/
│   ├── plant_disease_detection.py# Leaf disease classifier API
│   ├── model.tflite / weights    # CNN model weights
│   └── requirements.txt
│
├── Yield Prediction/
│   ├── Yield_prediction.py       # Yield prediction service
│   ├── yield_model.pkl           # Random Forest yield regressor
│   ├── crop_encoder.pkl          # Multi-crop LabelEncoder
│   └── soil_encoder.pkl          # Soil quality encoder
│
├── scripts/
│   ├── fetch_market_data.py      # Data extraction script for GitHub Actions
│   └── seed_market_data.py       # Baseline mandi market price seeder
│
├── ai_assistant.py               # Conversational AI chatbot service
├── market_analysis.py            # Mandi prices & market advisory service
├── weather_service.py            # Hyperlocal forecast & advisory service
├── all.py                        # Local runner starting all 8 services
│
├── index.html                    # Single-Page Application (SPA) dashboard
├── style.css                     # Comprehensive custom UI styles
├── web.js                        # Frontend controller & API integration
├── render.yaml                   # Infrastructure-as-code for Render deployment
└── requirements.txt              # Root Python dependencies
```

---

## 🚀 Getting Started (Local Development)

### 1. Prerequisites
* Python 3.10+ installed
* Git installed
* Access to a PostgreSQL instance (e.g., [Neon](https://neon.tech))
* Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/)

### 2. Clone the Repository
```bash
git clone https://github.com/UditJain7125/Krishi-Sanchar.git
cd Krishi-Sanchar
```

### 3. Create Virtual Environment & Install Dependencies
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root directory:
```env
DATABASE_URL=postgresql://user:password@ep-sample-pooler.neon.tech/krishisanchar?sslmode=require
GEMINI_API_KEY=your_gemini_api_key_here
MARKETPRICE_API_KEY=your_data_gov_in_api_key_here
```

### 5. Start All 8 Microservices Simultaneously
Run the built-in multi-service orchestrator:
```bash
python all.py
```
This automatically boots all 8 services on their assigned ports:
* Crop: `http://localhost:8000`
* Fertilizer: `http://localhost:8001`
* Yield: `http://localhost:8002`
* Market: `http://localhost:8003`
* Weather: `http://localhost:8004`
* AI Assistant: `http://localhost:8005`
* Disease Detection: `http://localhost:8006`
* Auth & Profile: `http://localhost:8007`

### 6. Launch Frontend
Open `index.html` in your web browser or run with a local server:
```bash
python -m http.server 5500
```
Visit `http://localhost:5500` in your browser.

---

## ☁️ Cloud Deployment Architecture

1. **Frontend Hosting:** Deployed on **GitHub Pages** tracking the `main` branch.
2. **Backend Microservices:** Deployed on **Render** as individual Web Services orchestrated via `render.yaml`.
3. **Database:** Hosted on **Neon.tech** (PostgreSQL Serverless).
4. **Automations:** **GitHub Actions** runs scheduled headless cron runners to keep government market data synchronized without loading the primary application server.

---

## 🔒 Security & Best Practices

* **Zero Hardcoded Secrets:** All credentials, database connection strings, and API keys are managed exclusively via environment variables.
* **Database Connection Pooling:** SQLAlchemy configured with `pool_pre_ping=True` and connection recycles to gracefully handle serverless database auto-suspension.
* **Dual-Layer Resilience:** Market price queries leverage localized PostgreSQL caching to guarantee 100% uptime even during government API gateway outages.
* **Token-Based Sessions:** Stateless JWT authentication tokens with client-side expiration handling.

---

## 👨‍💻 Author & Contributions

* **Author:** Udit Jain ([@UditJain7125](https://github.com/UditJain7125))
* **Project:** KrishiSanchar - Smart Agriculture Platform

---
*Empowering Indian Agriculture through Intelligent Technology.* 🌾🇮🇳

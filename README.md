# Stryder AI
**Agentic Multi-Agent Logistics Intelligence Platform**

![Stryder AI Header](https://via.placeholder.com/1200x400.png?text=STRYDER+AI) *(Add your banner here)*

🚀 **Live Deployment**: [https://stryder-ai.vercel.app](https://stryder-ai.vercel.app)

---

## 📖 Overview

**Stryder AI** is a next-generation logistics intelligence and simulation platform. Leveraging cutting-edge technologies, it operates a simulated global supply chain world state, enriched with dynamic machine learning models (ETA prediction, port congestion) and orchestrator AI agents powered by Groq. 

Stryder AI features both a stunning cinematic glassmorphism landing page and a robust React-based dashboard visualizing real-time operations, chaos events, and agentic decision-making on a live map.

---

## ✨ Key Features

- **Multi-Agent Orchestrator**: Uses GROQ-powered AI agents to autonomously manage logistics operations, respond to simulated chaos, and self-heal routes.
- **Dynamic Simulation Engine**: A continuous tick loop simulation of shipments, carriers, warehouses, and ports running in Python. Incorporates randomized "chaos events".
- **Advanced Machine Learning**: Integrated LightGBM/XGBoost/Scikit-learn models for predicting ETAs and Hub Congestion, built on OSMnx spatial intel.
- **Real-Time World Map**: A React-Leaflet dashboard displaying active shipments and global ops states.
- **Glassmorphism Landing Page**: A cinematic tech-noir static landing page designed with an immersive background video loop.
- **Supabase Persistence**: Real-time push synchronization from the simulation engine to a Supabase database.

---

## 🏗️ Architecture & Tech Stack

The project is split into three main interconnected components:

1. **Frontend Landing Page (Static/Vanilla Hub)**
   - HTML5, Vanilla JavaScript, CSS variables (Aesthetic: Tech-Noir Glassmorphism)
   - Served natively via generic HTTP serve.
2. **Frontend Dashboard (React SPA)**
   - **Framework**: React 19 + Vite
   - **Maps**: Leaflet + React Leaflet
   - **UI**: React Resizable Panels
   - **State/API**: Supabase JS Client, React Router DOM
3. **Backend Service (Python/FastAPI)**
   - **API Framework**: FastAPI, Uvicorn, Gunicorn
   - **AI/Agents**: Groq API
   - **Machine Learning**: Scikit-Learn, XGBoost, LightGBM, Pandas, Numpy
   - **Geospatial**: OSMnx, NetworkX, Geopy, Folium
   - **Database**: Supabase Python SDK

---

## 📂 Project Structure

```text
Stryder AI/
├── index.html            # Landing page definition
├── styles.css            # Landing page glassmorphism design system
├── script.js             # Landing page interaction & video looping
├── design.md             # STRYDER design documentation
├── assets/               # Video and static assets (bg.mp4)
├── backend/              # FastAPI Python Backend
│   ├── agents/           # LLM agent definitions (Orchestrators)
│   ├── data_pipeline/    # Data ingest & cleaning
│   ├── ml_models/        # ETA and Congestion ML models
│   ├── routers/          # FastAPI route controllers
│   ├── services/         # Supabase client / external services
│   └── simulation/       # World state tick-loop & logistics sim
├── frontend/             # React Vite Dashboard App
│   ├── src/              # React code / Map views / UI panels
│   └── package.json    
├── supabase/             # Local Supabase configurations
├── requirements.txt      # Backend Python dependencies
└── package.json          # Root package.json (Landing page server)
```

---

## 🚀 Getting Started

### Prerequisites
- Node.js 18+ and npm
- Python 3.10+
- Supabase Project (URL and Anon/Service Role Keys)
- Groq API Key

### 1. Environment Setup

Copy `.env.example` to `.env.local` in the root:
```bash
cp .env.example .env.local
```
Update the required variables inside `.env.local` (Supabase Keys, Groq API Key).

In the `frontend/` directory, create a `.env` file:
```bash
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_BACKEND_URL=http://localhost:8000
```

### 2. Running the Backend Server (FastAPI)

1. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the FastAPI development server:
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```
   *The API will be available at `http://localhost:8000/docs`.*

### 3. Running the React Dashboard (Vite)

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```
   *The dashboard will run on `http://localhost:5173`.*

### 4. Running the Landing Page

To view the cinematic landing page locally:
1. In the root directory, run:
   ```bash
   npm run start
   ```
   *Or manually using `npx serve .`*

---

## 🌐 Deployment

The system is configured for seamless deployment:
- **Frontend / Landing Pages**: Deployed via Vercel — **[stryder-ai.vercel.app](https://stryder-ai.vercel.app)**.
- **Backend API**: Structured with `gunicorn` and `Procfile` for deploying on environments like Render, Heroku, or AWS.
- **Database**: Managed centrally via Supabase cloud.

---

## 🛡️ License & Contact

**STRYDER AI** - *Internal/Proprietary*.
For inquiries or ops simulation adjustments, consult the DevOps and AI engineering leads.

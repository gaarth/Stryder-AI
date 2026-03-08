# Stryder-AI


# Deployed Link

https://stryder-ai.vercel.app/

AI-Driven Logistics Control Tower & Multi-Agent Simulation Platform

Stryder AI is an autonomous logistics operations simulator that demonstrates how specialized AI agents can monitor, analyze, and optimize complex shipping networks in real time.

The platform simulates shipments, warehouses, ports, and disruptions across a logistics network and uses coordinated AI agents to detect problems, optimize routes, reduce delays, and manage costs.

It combines a simulation engine, multi-agent orchestration system, real-time dashboards, and a command terminal for interacting with the agents.

# Core Features
Multi-Agent AI System

Stryder uses a coordinated set of AI agents, each responsible for a specific logistics function:

Sentinel
Monitors the system for anomalies and disruptions.

Strategist
Designs optimization strategies for shipments.

Actuary
Calculates cost and time tradeoffs.

Executor
Applies system fixes such as reroutes or carrier switches.

Cascade
Predicts cascading failures and systemic risks.

Specialized Strategist Models

The strategist agent can delegate analysis to specialized models:

ETA Agent
Optimizes shipment delivery times.

Delay Agent
Analyzes delays and delay risk.

Carrier Agent
Evaluates carrier performance and alternatives.

Hub Agent
Optimizes warehouse and hub routing.

Cascade Model
Predicts downstream disruption effects.

# Shipping Terminal

A Bloomberg-style operations terminal showing:

• Live shipment tracking
• Ports and warehouses
• Shipment routes
• AI agent decisions
• Disruption events

Users can inject disruptions or interact directly with agents.

Scenario Simulation

Two types of disruptions can be triggered:

Random Disruptions
Simulate unexpected real-world logistics problems.

Scenario Injection
Deterministic scenarios used for demos and testing.

Examples include:

Port congestion
Carrier strike
Weather disruption
Warehouse overflow
Customs delays

Interactive AI Command Interface

Users can interact with the system using agent tags:

# Supported agents

@Sentinel
@Strategist
@Actuary
@Executor
@Cascade

# Strategist subagents:

@Strategist:ETA_AGENT
@Strategist:DELAY_AGENT
@Strategist:CARRIER_AGENT
@Strategist:HUB_AGENT
@Strategist:CASCADE_MODEL

Example queries:

@Strategist:ETA_AGENT
What is the ETA for shipment 42?

@Strategist
Optimize shipment 26 for lower cost.

@Cascade
Are there any cascading risks in the network?

Autonomous Mode

The system supports two operating modes.

Manual Mode
Agents analyze problems but wait for approval.

Auto Mode
Agents automatically detect, analyze, and resolve disruptions.

Simulation Controls

For demonstrations, the simulation engine can be controlled using the terminal navbar.

Controls include:

Pause / Resume
Freeze Simulation
Step Tick
Simulation Speed
Movement Scale

This allows the system to be slowed down or frozen during demos.

# Dashboard

The dashboard provides operational insight into system behavior.

Agent Learning Hub
Chronological logs of what agents have learned.

Cascade Intelligence Center
Predicted disruptions and systemic risks.

Agent Replay System
Replay past disruptions and observe how agents responded.

System Architecture

Frontend
React + Vite dashboard and terminal UI

Backend
FastAPI simulation engine and agent orchestrator

Database
Supabase for persistent system state

AI Models
Groq LLM (Llama-3.3-70B-Versatile)

# Repository Structure
project-root
│
├── backend
│   ├── agents
│   ├── orchestrator
│   ├── simulation
│   ├── api
│   └── main.py
│
├── frontend
│   ├── components
│   ├── pages
│   ├── terminal
│   └── map
│
├── supabase
│   ├── schema.sql
│   ├── seed.sql
│   └── config
│
├── data
│   └── raw
│
└── README.md

#Local Development Setup
Prerequisites

Python 3.10+
Node.js 18+
npm
Supabase account
Groq API key

Step 1 — Clone the Repository
git clone https://github.com/gaarth/Stryder-AI.git
cd stryder-ai
Step 2 — Backend Setup

Create a Python virtual environment.

python -m venv venv

Activate it.

Windows:

venv\Scripts\activate

Mac/Linux:

source venv/bin/activate

Install dependencies.

pip install -r requirements.txt
Step 3 — Environment Variables

Create a .env file in the backend folder.

Example:

GROQ_API_KEY=your_groq_key

SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

BACKEND_CORS_ORIGINS=http://localhost:5173
Step 4 — Start the Backend
cd backend
uvicorn main:app --port 8000

Backend will run at:

http://localhost:8000
Step 5 — Frontend Setup

Open a new terminal.

cd frontend
npm install

Run the dev server.

npm run dev

Frontend will run at:

http://localhost:5173
Running the Full System

Start backend on port 8000

Start frontend on port 5173

Open the frontend URL

Interact with the shipping terminal

You can now:

Inject disruptions
Interact with agents
Optimize shipments
Replay events
Monitor cascade risks



#Deployed Link: 

https://stryder-ai.vercel.app/

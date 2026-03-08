"""
STRYDER AI - Backend Configuration
====================================
Loads environment variables from .env.local (local dev) or
system environment (production on Render).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env.local from project root (ignored in production)
PROJECT_ROOT = Path(__file__).parent.parent
ENV_PATH = PROJECT_ROOT / ".env.local"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# --- Supabase ---
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# --- Groq LLM ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# --- Backend ---
BACKEND_HOST = os.getenv("HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("PORT", "8000"))
CORS_ORIGINS = os.getenv(
    "BACKEND_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173"
).split(",")

# --- Paths ---
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "kaggle datasets"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DATA_SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"
SAVED_MODELS_DIR = Path(__file__).parent / "ml_models" / "saved_models"

# Ensure output dirs exist
DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
DATA_SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)

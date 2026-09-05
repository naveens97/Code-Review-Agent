"""
Central configuration for the Code Review Agent backend.

Everything here can be overridden with environment variables, so the same
code works unmodified in local dev, CI, and a real deployment.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # --- General ---
    DEBUG = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    PORT = int(os.environ.get("PORT", 5000))
    HOST = os.environ.get("HOST", "0.0.0.0")

    # --- Request limits ---
    MAX_CODE_LENGTH = int(os.environ.get("MAX_CODE_LENGTH", 50_000))  # characters
    MAX_STDIN_LENGTH = int(os.environ.get("MAX_STDIN_LENGTH", 10_000))

    # --- Execution sandbox ---
    EXECUTION_PROVIDER = os.environ.get("EXECUTION_PROVIDER", "local")  # "local" | "judge0"
    EXECUTION_TIMEOUT_SECONDS = int(os.environ.get("EXECUTION_TIMEOUT_SECONDS", 8))
    EXECUTION_MEMORY_MB = int(os.environ.get("EXECUTION_MEMORY_MB", 128))
    EXECUTION_MAX_OUTPUT_CHARS = int(os.environ.get("EXECUTION_MAX_OUTPUT_CHARS", 20_000))

    # --- Judge0 (optional, see executor/judge0_provider.py) ---
    JUDGE0_URL = os.environ.get("JUDGE0_URL", "https://judge0-ce.p.rapidapi.com")
    JUDGE0_API_KEY = os.environ.get("JUDGE0_API_KEY", "")

    # --- Static analysis ---
    PYLINT_TIMEOUT_SECONDS = int(os.environ.get("PYLINT_TIMEOUT_SECONDS", 15))
    BANDIT_TIMEOUT_SECONDS = int(os.environ.get("BANDIT_TIMEOUT_SECONDS", 15))
    MAX_CYCLOMATIC_COMPLEXITY = int(os.environ.get("MAX_CYCLOMATIC_COMPLEXITY", 10))
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

    # --- Storage ---
    DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
    DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(DATA_DIR, "history.db"))
    HISTORY_LIMIT_DEFAULT = int(os.environ.get("HISTORY_LIMIT_DEFAULT", 50))

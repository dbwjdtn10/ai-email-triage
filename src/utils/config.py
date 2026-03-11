import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent

# LLM 설정
PRIMARY_LLM = os.getenv("PRIMARY_LLM", "gpt-4o-mini")
FALLBACK_LLM = os.getenv("FALLBACK_LLM", "claude-haiku-4-5-20251001")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))

# DB
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'data' / 'triage.db'}")
DATABASE_PATH = PROJECT_ROOT / "data" / "triage.db"

# API
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# 에이전트 설정
MAX_REVISION_COUNT = 2
CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.7

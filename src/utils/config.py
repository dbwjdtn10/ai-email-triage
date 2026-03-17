"""설정 관리 - Pydantic Settings 기반 타입 안전 설정"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경 변수 기반 애플리케이션 설정 (자동 타입 검증 + .env 로딩)"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM 설정
    primary_llm: str = Field(default="gpt-4o-mini", alias="PRIMARY_LLM")
    fallback_llm: str = Field(default="claude-haiku-4-5-20251001", alias="FALLBACK_LLM")
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0, alias="LLM_TEMPERATURE")
    llm_max_retries: int = Field(default=2, ge=0, alias="LLM_MAX_RETRIES")

    # API 설정
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, ge=1, le=65535, alias="API_PORT")

    # Rate Limiting
    rate_limit_process: str = Field(
        default="30/minute", alias="RATE_LIMIT_PROCESS",
        description="단건 처리 엔드포인트 레이트 리밋",
    )
    rate_limit_batch: str = Field(
        default="5/minute", alias="RATE_LIMIT_BATCH",
        description="배치 처리 엔드포인트 레이트 리밋",
    )

    # 배치 처리
    max_concurrent_emails: int = Field(
        default=5, ge=1, le=20, alias="MAX_CONCURRENT_EMAILS",
        description="배치 처리 시 최대 동시 처리 수",
    )

    # API 인증
    api_key: str = Field(
        default="", alias="API_KEY",
        description="API 인증 키 (빈 문자열이면 인증 비활성화)",
    )

    # 에이전트 설정
    max_revision_count: int = Field(default=2, ge=1)
    classification_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    @property
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    @property
    def database_path(self) -> Path:
        return self.project_root / "data" / "triage.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()


# 하위 호환 - 기존 코드에서 직접 참조하는 상수들
settings = get_settings()
PROJECT_ROOT = settings.project_root
PRIMARY_LLM = settings.primary_llm
FALLBACK_LLM = settings.fallback_llm
LLM_TEMPERATURE = settings.llm_temperature
LLM_MAX_RETRIES = settings.llm_max_retries
DATABASE_PATH = settings.database_path
API_HOST = settings.api_host
API_PORT = settings.api_port
MAX_REVISION_COUNT = settings.max_revision_count
CLASSIFICATION_CONFIDENCE_THRESHOLD = settings.classification_confidence_threshold

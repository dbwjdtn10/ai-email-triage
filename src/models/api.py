"""API 전용 요청/응답 스키마 - 구조화된 에러 응답 포함"""

from typing import Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """표준화된 에러 응답 모델 (RFC 7807 Problem Details 간소화)"""

    code: str = Field(description="에러 코드 (예: RATE_LIMITED, PROCESSING_FAILED)")
    message: str = Field(description="사람이 읽을 수 있는 에러 메시지")
    detail: Optional[str] = Field(default=None, description="디버깅용 상세 정보")
    request_id: Optional[str] = Field(default=None, description="요청 추적 ID")


class BatchResult(BaseModel):
    """배치 처리 개별 결과"""

    email_id: str
    status: str = Field(description="success 또는 error")
    result: Optional[dict] = None
    error: Optional[str] = None


class BatchResponse(BaseModel):
    """배치 처리 응답"""

    total: int
    succeeded: int
    failed: int
    results: list[BatchResult]


class TokenUsageResponse(BaseModel):
    """토큰 사용량 응답"""

    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    llm_calls: int = 0

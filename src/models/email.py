"""Pydantic 모델 - 이메일 입력 및 에이전트 출력 스키마"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

# ── 입력 스키마 ──

class EmailInput(BaseModel):
    email_id: str
    sender: str
    subject: str
    body: str
    received_at: str


# ── 에이전트별 Structured Output 스키마 ──

class ClassificationResult(BaseModel):
    """분류 에이전트 출력"""
    category: Literal["inquiry", "complaint", "suggestion", "spam", "other"] = Field(
        description="이메일 카테고리"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="분류 신뢰도 (0.0~1.0)")
    reason: str = Field(description="분류 근거")


class PriorityResult(BaseModel):
    """우선순위 에이전트 출력"""
    priority: Literal["high", "medium", "low"] = Field(description="긴급도")
    reason: str = Field(description="우선순위 판단 근거")
    keywords: list[str] = Field(default_factory=list, description="판단에 사용된 핵심 키워드")


class SentimentResult(BaseModel):
    """감정 분석 에이전트 출력"""
    sentiment: Literal["positive", "negative", "neutral", "urgent"] = Field(
        description="감정 톤"
    )
    intensity: float = Field(ge=0.0, le=1.0, description="감정 강도 (0.0~1.0)")
    summary: str = Field(description="감정 분석 요약")


class DraftResult(BaseModel):
    """응답 초안 생성 에이전트 출력"""
    response: str = Field(description="응답 초안 본문")
    tone: str = Field(description="사용한 톤 (formal/empathetic/friendly)")
    key_points: list[str] = Field(description="응답에 포함한 핵심 포인트")


class ReviewResult(BaseModel):
    """검토 에이전트 출력"""
    decision: Literal["approved", "needs_revision", "rejected"] = Field(
        description="검토 결과"
    )
    feedback: str = Field(description="검토 피드백")
    tone_check: bool = Field(description="톤 적절성 통과 여부")
    accuracy_check: bool = Field(description="사실 정확성 통과 여부")
    completeness_check: bool = Field(description="정보 완전성 통과 여부")


# ── 최종 처리 결과 ──

class TriageResult(BaseModel):
    """전체 파이프라인 처리 결과"""
    email_id: str
    category: str
    category_confidence: float
    priority: str
    priority_reason: str
    sentiment: str
    sentiment_intensity: float
    draft_response: Optional[str] = None
    review_decision: Optional[str] = None
    review_feedback: Optional[str] = None
    final_response: Optional[str] = None
    human_approved: Optional[bool] = None
    processing_log: list[str] = Field(default_factory=list)

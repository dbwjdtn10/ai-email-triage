"""LangGraph 상태 정의 - 모든 노드가 공유하는 상태"""

from operator import add
from typing import Annotated, Literal, Optional

from typing_extensions import TypedDict


class EmailState(TypedDict):
    # ── 입력 ──
    email_id: str
    sender: str
    subject: str
    body: str
    received_at: str

    # ── 분류 결과 ──
    category: Literal["inquiry", "complaint", "suggestion", "spam", "other"]
    category_confidence: float
    category_reason: str

    # ── 우선순위 ──
    priority: Literal["high", "medium", "low"]
    priority_reason: str
    priority_keywords: list[str]

    # ── 감정 분석 (병렬 실행) ──
    sentiment: Literal["positive", "negative", "neutral", "urgent"]
    sentiment_intensity: float
    sentiment_summary: str

    # ── 응답 생성 ──
    draft_response: str
    draft_tone: str
    draft_key_points: list[str]

    # ── 검토 ──
    review_decision: Literal["approved", "needs_revision", "rejected"]
    review_feedback: str
    revision_count: int

    # ── 최종 ──
    final_response: Optional[str]
    human_approved: Optional[bool]

    # ── 토큰 사용량 (최신 스냅샷으로 갱신) ──
    token_usage: Optional[dict]

    # ── 메타 (Annotated[list, add]로 로그 누적) ──
    processing_log: Annotated[list[str], add]

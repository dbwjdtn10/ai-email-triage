"""테스트 설정 및 공통 fixture"""

from unittest.mock import MagicMock

import pytest

from src.models.email import (
    ClassificationResult,
    DraftResult,
    PriorityResult,
    ReviewResult,
    SentimentResult,
)


@pytest.fixture
def sample_email_state():
    return {
        "email_id": "test_001",
        "sender": "test@example.com",
        "subject": "긴급: 서비스 장애",
        "body": "오전부터 서비스가 다운되었습니다. 즉시 확인해주세요.",
        "received_at": "2025-03-10T09:00:00Z",
        "revision_count": 0,
        "processing_log": [],
    }


@pytest.fixture
def spam_email_state():
    return {
        "email_id": "test_spam",
        "sender": "promo@spam.com",
        "subject": "축하합니다! 당첨!",
        "body": "지금 클릭하세요! 상금을 수령하세요!",
        "received_at": "2025-03-10T10:00:00Z",
        "revision_count": 0,
        "processing_log": [],
    }


@pytest.fixture
def classified_state(sample_email_state):
    return {
        **sample_email_state,
        "category": "complaint",
        "category_confidence": 0.92,
        "category_reason": "서비스 장애 보고",
        "sentiment": "urgent",
        "sentiment_intensity": 0.9,
        "sentiment_summary": "긴급한 상황으로 불안과 절박함 표현",
        "priority": "high",
        "priority_reason": "서비스 장애로 인한 긴급 대응 필요",
        "priority_keywords": ["긴급", "장애", "다운"],
    }


@pytest.fixture
def mock_llm():
    """LLM 호출을 모킹하는 fixture"""
    llm = MagicMock()
    return llm


@pytest.fixture
def mock_classification_result():
    return ClassificationResult(
        category="complaint",
        confidence=0.92,
        reason="서비스 장애 보고",
    )


@pytest.fixture
def mock_priority_result():
    return PriorityResult(
        priority="high",
        reason="서비스 장애로 긴급 대응 필요",
        keywords=["긴급", "장애", "다운"],
    )


@pytest.fixture
def mock_sentiment_result():
    return SentimentResult(
        sentiment="urgent",
        intensity=0.9,
        summary="긴급한 상황으로 불안과 절박함 표현",
    )


@pytest.fixture
def mock_draft_result():
    return DraftResult(
        response="안녕하세요, 불편을 드려 죄송합니다. 현재 기술팀에서 긴급 대응 중입니다.",
        tone="empathetic",
        key_points=["사과", "현황 공유", "대응 중"],
    )


@pytest.fixture
def mock_review_result():
    return ReviewResult(
        decision="approved",
        feedback="톤과 내용이 적절합니다.",
        tone_check=True,
        accuracy_check=True,
        completeness_check=True,
    )

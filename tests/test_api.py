"""API 엔드포인트 통합 테스트"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_workflow():
    """워크플로우 모킹 - 실제 LLM 호출 방지"""
    mock_state = {
        "email_id": "test_001",
        "sender": "test@example.com",
        "subject": "테스트 이메일",
        "body": "테스트 본문입니다.",
        "category": "inquiry",
        "category_confidence": 0.95,
        "priority": "medium",
        "priority_reason": "일반 문의",
        "sentiment": "neutral",
        "sentiment_intensity": 0.3,
        "draft_response": "안녕하세요, 문의 감사합니다.",
        "final_response": "안녕하세요, 문의 감사합니다.",
        "review_decision": "approved",
        "revision_count": 0,
        "processing_log": ["[분류] inquiry", "[감정분석] neutral"],
        "token_usage": {
            "total_tokens": 150,
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "estimated_cost_usd": 0.0001,
            "llm_calls": 1,
        },
    }

    mock_wf = MagicMock()
    mock_wf.invoke.return_value = mock_state

    with patch("src.api.routes._get_workflow", return_value=mock_wf), \
         patch("src.api.routes.save_result"):
        yield mock_wf


class TestHealthCheck:
    def test_health_returns_ok(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.2.0"


class TestProcessEmail:
    def test_process_success(self):
        response = client.post("/api/v1/process", json={
            "sender": "user@example.com",
            "subject": "문의합니다",
            "body": "제품에 대해 궁금한 점이 있습니다.",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "inquiry"
        assert data["priority"] == "medium"
        assert data["processing_log"]

    def test_process_with_custom_email_id(self):
        response = client.post("/api/v1/process", json={
            "sender": "user@example.com",
            "subject": "문의합니다",
            "body": "테스트",
            "email_id": "custom_123",
        })
        assert response.status_code == 200

    def test_process_includes_token_usage(self):
        response = client.post("/api/v1/process", json={
            "sender": "user@example.com",
            "subject": "테스트",
            "body": "테스트 본문",
        })
        data = response.json()
        assert data["token_usage"] is not None
        assert data["token_usage"]["total_tokens"] == 150

    def test_process_empty_subject_returns_422(self):
        response = client.post("/api/v1/process", json={
            "sender": "user@example.com",
            "subject": "",
            "body": "본문",
        })
        assert response.status_code == 422

    def test_process_missing_body_returns_422(self):
        response = client.post("/api/v1/process", json={
            "sender": "user@example.com",
            "subject": "제목",
        })
        assert response.status_code == 422


class TestBatchProcess:
    def test_batch_success(self):
        response = client.post("/api/v1/batch", json=[
            {"sender": "a@test.com", "subject": "문의1", "body": "본문1"},
            {"sender": "b@test.com", "subject": "문의2", "body": "본문2"},
        ])
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["succeeded"] == 2
        assert data["failed"] == 0

    def test_batch_empty_list(self):
        response = client.post("/api/v1/batch", json=[])
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestHistory:
    @patch("src.api.routes.get_history", return_value=[])
    def test_history_default(self, mock_hist):
        response = client.get("/api/v1/history")
        assert response.status_code == 200
        mock_hist.assert_called_once_with(limit=10, priority=None, category=None)

    @patch("src.api.routes.get_history", return_value=[])
    def test_history_with_filters(self, mock_hist):
        response = client.get("/api/v1/history?limit=5&priority=high&category=complaint")
        assert response.status_code == 200
        mock_hist.assert_called_once_with(limit=5, priority="high", category="complaint")


class TestStats:
    @patch("src.api.routes.get_stats", return_value={
        "total": 10,
        "by_category": {"inquiry": 5},
        "by_priority": {"high": 2},
        "by_sentiment": {"neutral": 6},
        "avg_processing_time_ms": 2500.0,
        "total_tokens_used": 1500,
        "total_cost_usd": 0.005,
    })
    def test_stats_includes_token_info(self, mock_stats):
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_tokens_used"] == 1500
        assert data["total_cost_usd"] == 0.005


class TestMiddleware:
    def test_response_has_request_id(self):
        response = client.get("/api/v1/health")
        assert "X-Request-ID" in response.headers

    def test_response_has_process_time(self):
        response = client.get("/api/v1/health")
        assert "X-Process-Time" in response.headers
        assert float(response.headers["X-Process-Time"]) >= 0

    def test_custom_request_id_is_preserved(self):
        response = client.get(
            "/api/v1/health",
            headers={"X-Request-ID": "my-custom-id"},
        )
        assert response.headers["X-Request-ID"] == "my-custom-id"

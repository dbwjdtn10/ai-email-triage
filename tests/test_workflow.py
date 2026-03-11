"""워크플로우 통합 테스트"""

from unittest.mock import MagicMock

from src.graph.edges import check_review_result, route_by_priority, should_require_human_approval


class TestEdges:
    def test_route_spam(self):
        state = {"category": "spam", "priority": "low"}
        assert route_by_priority(state) == "spam"

    def test_route_high_priority(self):
        state = {"category": "complaint", "priority": "high"}
        assert route_by_priority(state) == "alert_and_draft"

    def test_route_medium_priority(self):
        state = {"category": "inquiry", "priority": "medium"}
        assert route_by_priority(state) == "draft_only"

    def test_route_low_priority(self):
        state = {"category": "suggestion", "priority": "low"}
        assert route_by_priority(state) == "draft_only"

    def test_review_approved(self):
        state = {"review_decision": "approved"}
        assert check_review_result(state) == "approved"

    def test_review_needs_revision(self):
        state = {"review_decision": "needs_revision"}
        assert check_review_result(state) == "needs_revision"

    def test_review_rejected(self):
        state = {"review_decision": "rejected"}
        assert check_review_result(state) == "rejected"

    def test_human_approval_required_for_high(self):
        state = {"priority": "high"}
        assert should_require_human_approval(state) == "human_approval"

    def test_auto_approve_for_medium(self):
        state = {"priority": "medium"}
        assert should_require_human_approval(state) == "auto_approve"


class TestReviewerMaxRevision:
    def test_max_revision_forces_approval(self, classified_state):
        from src.agents.reviewer import ReviewerAgent
        from src.models.email import ReviewResult

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = MagicMock()

        agent = ReviewerAgent(mock_llm)
        agent.chain = MagicMock()
        agent.chain.invoke.return_value = ReviewResult(
            decision="needs_revision",
            feedback="톤 수정 필요",
            tone_check=False,
            accuracy_check=True,
            completeness_check=True,
        )

        state = {
            **classified_state,
            "draft_response": "테스트 응답",
            "revision_count": 2,  # MAX_REVISION_COUNT
        }

        result = agent.run(state)
        assert result["review_decision"] == "approved"
        assert "자동 승인" in result["review_feedback"]

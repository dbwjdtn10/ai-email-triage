"""분류 에이전트 테스트"""

from unittest.mock import MagicMock

from src.agents.classifier import ClassifierAgent
from src.models.email import ClassificationResult


class TestClassifierAgent:
    def test_classify_complaint(self, sample_email_state, mock_classification_result):
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured

        # chain invoke 결과 설정
        agent = ClassifierAgent(mock_llm)
        agent.chain = MagicMock()
        agent.chain.invoke.return_value = mock_classification_result

        result = agent.run(sample_email_state)

        assert result["category"] == "complaint"
        assert result["category_confidence"] == 0.92
        assert len(result["processing_log"]) == 1

    def test_low_confidence_fallback_to_other(self, sample_email_state):
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = MagicMock()

        agent = ClassifierAgent(mock_llm)
        agent.chain = MagicMock()
        agent.chain.invoke.return_value = ClassificationResult(
            category="inquiry",
            confidence=0.5,
            reason="불확실한 분류",
        )

        result = agent.run(sample_email_state)

        assert result["category"] == "other"
        assert result["category_confidence"] == 0.5

    def test_spam_classification(self, spam_email_state):
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = MagicMock()

        agent = ClassifierAgent(mock_llm)
        agent.chain = MagicMock()
        agent.chain.invoke.return_value = ClassificationResult(
            category="spam",
            confidence=0.98,
            reason="전형적인 스팸 패턴",
        )

        result = agent.run(spam_email_state)

        assert result["category"] == "spam"
        assert result["category_confidence"] == 0.98

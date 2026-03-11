"""우선순위 에이전트 테스트"""

from unittest.mock import MagicMock

from src.agents.prioritizer import PrioritizerAgent
from src.models.email import PriorityResult


class TestPrioritizerAgent:
    def test_high_priority(self, classified_state, mock_priority_result):
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = MagicMock()

        agent = PrioritizerAgent(mock_llm)
        agent.chain = MagicMock()
        agent.chain.invoke.return_value = mock_priority_result

        result = agent.run(classified_state)

        assert result["priority"] == "high"
        assert "긴급" in result["priority_keywords"]
        assert len(result["processing_log"]) == 1

    def test_low_priority(self, classified_state):
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = MagicMock()

        agent = PrioritizerAgent(mock_llm)
        agent.chain = MagicMock()
        agent.chain.invoke.return_value = PriorityResult(
            priority="low",
            reason="뉴스레터성 메일",
            keywords=["뉴스레터"],
        )

        result = agent.run(classified_state)
        assert result["priority"] == "low"

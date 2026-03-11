"""우선순위 에이전트 - 긴급도 판단"""

from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from src.graph.state import EmailState
from src.models.email import PriorityResult

SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "prioritizer.txt").read_text(
    encoding="utf-8"
)

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """제목: {subject}
발신자: {sender}
카테고리: {category} (신뢰도: {category_confidence})
감정: {sentiment} (강도: {sentiment_intensity})

본문:
{body}"""),
])


class PrioritizerAgent:
    def __init__(self, llm: BaseChatModel):
        self.chain = PROMPT | llm.with_structured_output(PriorityResult)

    def run(self, state: EmailState) -> dict:
        result: PriorityResult = self.chain.invoke({
            "subject": state["subject"],
            "sender": state["sender"],
            "body": state["body"],
            "category": state["category"],
            "category_confidence": state["category_confidence"],
            "sentiment": state.get("sentiment", "neutral"),
            "sentiment_intensity": state.get("sentiment_intensity", 0.0),
        })

        return {
            "priority": result.priority,
            "priority_reason": result.reason,
            "priority_keywords": result.keywords,
            "processing_log": [
                f"[우선순위] {result.priority.upper()} - {result.reason}"
            ],
        }

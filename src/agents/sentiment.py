"""감정 분석 에이전트 - 이메일 감정 톤 분석 (분류와 병렬 실행)"""

from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from src.graph.state import EmailState
from src.models.email import SentimentResult

SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "sentiment.txt").read_text(
    encoding="utf-8"
)

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "제목: {subject}\n발신자: {sender}\n\n본문:\n{body}"),
])


class SentimentAgent:
    def __init__(self, llm: BaseChatModel):
        self.chain = PROMPT | llm.with_structured_output(SentimentResult)

    def run(self, state: EmailState) -> dict:
        result: SentimentResult = self.chain.invoke({
            "subject": state["subject"],
            "sender": state["sender"],
            "body": state["body"],
        })

        return {
            "sentiment": result.sentiment,
            "sentiment_intensity": result.intensity,
            "sentiment_summary": result.summary,
            "processing_log": [
                f"[감정분석] {result.sentiment} (강도: {result.intensity:.2f}) - {result.summary}"
            ],
        }

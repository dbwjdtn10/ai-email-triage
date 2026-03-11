"""분류 에이전트 - 이메일 카테고리 분류 (Structured Output)"""

from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from src.graph.state import EmailState
from src.models.email import ClassificationResult
from src.utils.config import CLASSIFICATION_CONFIDENCE_THRESHOLD

SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "classifier.txt").read_text(
    encoding="utf-8"
)

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "제목: {subject}\n발신자: {sender}\n\n본문:\n{body}"),
])


class ClassifierAgent:
    def __init__(self, llm: BaseChatModel):
        self.chain = PROMPT | llm.with_structured_output(ClassificationResult)

    def run(self, state: EmailState) -> dict:
        result: ClassificationResult = self.chain.invoke({
            "subject": state["subject"],
            "sender": state["sender"],
            "body": state["body"],
        })

        category = result.category
        if result.confidence < CLASSIFICATION_CONFIDENCE_THRESHOLD:
            category = "other"

        return {
            "category": category,
            "category_confidence": result.confidence,
            "category_reason": result.reason,
            "processing_log": [
                f"[분류] {category} (신뢰도: {result.confidence:.2f}) - {result.reason}"
            ],
        }

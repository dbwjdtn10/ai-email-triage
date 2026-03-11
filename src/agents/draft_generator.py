"""응답 생성 에이전트 - 카테고리/감정 기반 답변 초안 작성"""

from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from src.graph.state import EmailState
from src.models.email import DraftResult

SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "draft_generator.txt").read_text(
    encoding="utf-8"
)

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """## 원본 이메일
제목: {subject}
발신자: {sender}
본문:
{body}

## 분석 결과
- 카테고리: {category}
- 우선순위: {priority}
- 감정: {sentiment} (강도: {sentiment_intensity})
- 우선순위 근거: {priority_reason}

## 이전 검토 피드백 (있는 경우)
{review_feedback}

위 정보를 바탕으로 적절한 답변 초안을 작성하세요."""),
])


class DraftGeneratorAgent:
    def __init__(self, llm: BaseChatModel):
        self.chain = PROMPT | llm.with_structured_output(DraftResult)

    def run(self, state: EmailState) -> dict:
        review_feedback = state.get("review_feedback", "없음 (첫 작성)")

        result: DraftResult = self.chain.invoke({
            "subject": state["subject"],
            "sender": state["sender"],
            "body": state["body"],
            "category": state["category"],
            "priority": state["priority"],
            "sentiment": state.get("sentiment", "neutral"),
            "sentiment_intensity": state.get("sentiment_intensity", 0.0),
            "priority_reason": state.get("priority_reason", ""),
            "review_feedback": review_feedback,
        })

        revision_count = state.get("revision_count", 0)
        log_prefix = "[응답생성]" if revision_count == 0 else f"[응답수정 #{revision_count}]"

        return {
            "draft_response": result.response,
            "draft_tone": result.tone,
            "draft_key_points": result.key_points,
            "processing_log": [
                f"{log_prefix} 톤: {result.tone}, 핵심포인트: {', '.join(result.key_points)}"
            ],
        }

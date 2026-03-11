"""검토 에이전트 - 응답 초안 품질 검증 + 재작성 루프"""

from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from src.graph.state import EmailState
from src.models.email import ReviewResult
from src.utils.config import MAX_REVISION_COUNT

SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "reviewer.txt").read_text(
    encoding="utf-8"
)

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", """## 원본 이메일
제목: {subject}
본문:
{body}

## 분석 결과
- 카테고리: {category}
- 감정: {sentiment}
- 우선순위: {priority}

## 응답 초안
{draft_response}

## 수정 횟수: {revision_count} / {max_revisions}

위 응답 초안을 검토하세요."""),
])


class ReviewerAgent:
    def __init__(self, llm: BaseChatModel):
        self.chain = PROMPT | llm.with_structured_output(ReviewResult)

    def run(self, state: EmailState) -> dict:
        revision_count = state.get("revision_count", 0)

        result: ReviewResult = self.chain.invoke({
            "subject": state["subject"],
            "body": state["body"],
            "category": state["category"],
            "sentiment": state.get("sentiment", "neutral"),
            "priority": state["priority"],
            "draft_response": state["draft_response"],
            "revision_count": revision_count,
            "max_revisions": MAX_REVISION_COUNT,
        })

        # 최대 수정 횟수 초과 시 강제 승인
        decision = result.decision
        if decision == "needs_revision" and revision_count >= MAX_REVISION_COUNT:
            decision = "approved"
            result.feedback += " (최대 수정 횟수 도달로 자동 승인)"

        checks = (
            f"톤:{_icon(result.tone_check)} "
            f"정확성:{_icon(result.accuracy_check)} "
            f"완전성:{_icon(result.completeness_check)}"
        )

        new_state = {
            "review_decision": decision,
            "review_feedback": result.feedback,
            "processing_log": [f"[검토] {decision.upper()} ({checks}) - {result.feedback}"],
        }

        if decision == "needs_revision":
            new_state["revision_count"] = revision_count + 1

        if decision == "approved":
            new_state["final_response"] = state["draft_response"]

        return new_state


def _icon(passed: bool) -> str:
    return "PASS" if passed else "FAIL"

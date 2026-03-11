"""LangGraph 조건부 엣지 로직"""

from src.graph.state import EmailState


def route_by_priority(state: EmailState) -> str:
    """우선순위에 따른 분기"""
    if state["category"] == "spam":
        return "spam"
    if state["priority"] == "high":
        return "alert_and_draft"
    return "draft_only"


def check_review_result(state: EmailState) -> str:
    """검토 결과에 따른 분기 (재작성 루프 포함)"""
    decision = state.get("review_decision", "approved")
    if decision == "needs_revision":
        return "needs_revision"
    if decision == "rejected":
        return "rejected"
    return "approved"


def should_require_human_approval(state: EmailState) -> str:
    """HIGH 우선순위 건만 Human Approval 필요"""
    if state["priority"] == "high":
        return "human_approval"
    return "auto_approve"

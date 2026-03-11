"""LangGraph 워크플로우 조립 - 병렬 실행 + Checkpointer + Human-in-the-loop"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from src.graph.edges import check_review_result, route_by_priority
from src.graph.nodes import (
    analyze_sentiment,
    classify,
    generate_draft,
    mark_spam,
    prioritize,
    review_draft,
    send_alert,
)
from src.graph.state import EmailState
from src.utils.config import DATABASE_PATH


def build_workflow(checkpointer=None, use_sqlite: bool = False):
    """
    워크플로우를 빌드하고 컴파일합니다.

    Args:
        checkpointer: 커스텀 체크포인터. None이면 기본값 사용.
        use_sqlite: True면 SqliteSaver 사용 (영속 저장), False면 MemorySaver (인메모리)
    """
    workflow = StateGraph(EmailState)

    # ── 노드 등록 ──
    workflow.add_node("classify", classify)
    workflow.add_node("analyze_sentiment", analyze_sentiment)
    workflow.add_node("prioritize", prioritize)
    workflow.add_node("generate_draft", generate_draft)
    workflow.add_node("review_draft", review_draft)
    workflow.add_node("send_alert", send_alert)
    workflow.add_node("mark_spam", mark_spam)

    # ── 병렬 실행: 분류 + 감정분석 (Fan-out) ──
    # START → classify, analyze_sentiment 동시 실행
    workflow.add_edge(START, "classify")
    workflow.add_edge(START, "analyze_sentiment")

    # ── Fan-in: 둘 다 완료 후 우선순위 판단 ──
    workflow.add_edge("classify", "prioritize")
    workflow.add_edge("analyze_sentiment", "prioritize")

    # ── 조건부 라우팅: 우선순위에 따른 분기 ──
    workflow.add_conditional_edges(
        "prioritize",
        route_by_priority,
        {
            "spam": "mark_spam",
            "alert_and_draft": "send_alert",
            "draft_only": "generate_draft",
        },
    )

    workflow.add_edge("mark_spam", END)
    workflow.add_edge("send_alert", "generate_draft")
    workflow.add_edge("generate_draft", "review_draft")

    # ── 검토 결과에 따른 분기 (재작성 루프) ──
    workflow.add_conditional_edges(
        "review_draft",
        check_review_result,
        {
            "approved": END,
            "needs_revision": "generate_draft",
            "rejected": END,
        },
    )

    # ── 체크포인터 설정 ──
    if checkpointer is None:
        if use_sqlite:
            DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
            db_path = str(DATABASE_PATH.with_suffix(".checkpoint.db"))
            checkpointer = SqliteSaver.from_conn_string(db_path)
        else:
            checkpointer = MemorySaver()

    # ── 컴파일 (HIGH 건에서 Human Approval을 위해 interrupt) ──
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["generate_draft"],
    )


def build_workflow_auto(checkpointer=None, use_sqlite: bool = False):
    """
    interrupt 없는 자동 모드 워크플로우 (배치 처리, API 서빙용)
    """
    workflow = StateGraph(EmailState)

    workflow.add_node("classify", classify)
    workflow.add_node("analyze_sentiment", analyze_sentiment)
    workflow.add_node("prioritize", prioritize)
    workflow.add_node("generate_draft", generate_draft)
    workflow.add_node("review_draft", review_draft)
    workflow.add_node("send_alert", send_alert)
    workflow.add_node("mark_spam", mark_spam)

    workflow.add_edge(START, "classify")
    workflow.add_edge(START, "analyze_sentiment")
    workflow.add_edge("classify", "prioritize")
    workflow.add_edge("analyze_sentiment", "prioritize")

    workflow.add_conditional_edges(
        "prioritize",
        route_by_priority,
        {
            "spam": "mark_spam",
            "alert_and_draft": "send_alert",
            "draft_only": "generate_draft",
        },
    )

    workflow.add_edge("mark_spam", END)
    workflow.add_edge("send_alert", "generate_draft")
    workflow.add_edge("generate_draft", "review_draft")

    workflow.add_conditional_edges(
        "review_draft",
        check_review_result,
        {
            "approved": END,
            "needs_revision": "generate_draft",
            "rejected": END,
        },
    )

    if checkpointer is None:
        if use_sqlite:
            DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
            db_path = str(DATABASE_PATH.with_suffix(".checkpoint.db"))
            checkpointer = SqliteSaver.from_conn_string(db_path)
        else:
            checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)

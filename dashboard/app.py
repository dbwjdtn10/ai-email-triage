"""Streamlit 대시보드 - 이메일 트리아지 모니터링"""

import json
import sys
from pathlib import Path

import streamlit as st

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.repository import get_history, get_stats
from src.db.database import init_db

st.set_page_config(
    page_title="AI Email Triage Dashboard",
    page_icon="📧",
    layout="wide",
)

init_db()


def main():
    st.title("📧 AI Email Triage Dashboard")
    st.markdown("LangGraph 기반 멀티 에이전트 이메일 트리아지 시스템")

    # ── 사이드바: 필터 ──
    with st.sidebar:
        st.header("필터")
        priority_filter = st.selectbox("우선순위", [None, "high", "medium", "low"])
        category_filter = st.selectbox(
            "카테고리", [None, "inquiry", "complaint", "suggestion", "spam", "other"]
        )
        limit = st.slider("표시 건수", 5, 100, 20)

    # ── 통계 카드 ──
    try:
        stats = get_stats()
    except Exception:
        stats = {"total": 0, "by_category": {}, "by_priority": {}, "by_sentiment": {}, "avg_processing_time_ms": 0}

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("전체 처리", f"{stats['total']}건")
    with col2:
        high_count = stats["by_priority"].get("high", 0)
        st.metric("HIGH 우선순위", f"{high_count}건")
    with col3:
        complaint_count = stats["by_category"].get("complaint", 0)
        st.metric("불만 건수", f"{complaint_count}건")
    with col4:
        st.metric("평균 처리 시간", f"{stats['avg_processing_time_ms']:.0f}ms")

    # ── 차트 ──
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("카테고리 분포")
        if stats["by_category"]:
            st.bar_chart(stats["by_category"])
        else:
            st.info("데이터가 없습니다")

    with col_right:
        st.subheader("우선순위 분포")
        if stats["by_priority"]:
            st.bar_chart(stats["by_priority"])
        else:
            st.info("데이터가 없습니다")

    # ── 감정 분포 ──
    st.subheader("감정 분포")
    if stats["by_sentiment"]:
        st.bar_chart(stats["by_sentiment"])

    # ── 처리 이력 테이블 ──
    st.subheader("처리 이력")
    records = get_history(limit=limit, priority=priority_filter, category=category_filter)

    if records:
        display_data = []
        for r in records:
            display_data.append({
                "ID": r.get("email_id", "")[:12],
                "제목": r.get("subject", "")[:40],
                "카테고리": r.get("category", ""),
                "우선순위": r.get("priority", ""),
                "감정": r.get("sentiment", ""),
                "검토결과": r.get("review_decision", "-"),
                "처리시간(ms)": r.get("processing_time_ms", 0),
                "일시": r.get("created_at", ""),
            })
        st.dataframe(display_data, use_container_width=True)

        # ── 상세 보기 ──
        st.subheader("상세 보기")
        selected_idx = st.selectbox(
            "이메일 선택",
            range(len(records)),
            format_func=lambda i: f"{records[i].get('email_id', '')} - {records[i].get('subject', '')[:40]}",
        )

        if selected_idx is not None:
            record = records[selected_idx]
            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("**분석 결과**")
                st.json({
                    "category": record.get("category"),
                    "confidence": record.get("category_confidence"),
                    "priority": record.get("priority"),
                    "sentiment": record.get("sentiment"),
                    "sentiment_intensity": record.get("sentiment_intensity"),
                    "review_decision": record.get("review_decision"),
                })

            with col_b:
                st.markdown("**최종 응답**")
                response = record.get("final_response") or record.get("draft_response") or "응답 없음"
                st.text_area("응답", response, height=200, disabled=True)

            # 처리 로그
            log_str = record.get("processing_log", "[]")
            try:
                logs = json.loads(log_str) if isinstance(log_str, str) else log_str
                if logs:
                    st.markdown("**처리 로그**")
                    for log in logs:
                        st.text(f"  {log}")
            except Exception:
                pass
    else:
        st.info("처리 이력이 없습니다. CLI 또는 API로 이메일을 처리해 보세요.")

    # ── 수동 처리 ──
    st.divider()
    st.subheader("이메일 직접 처리")

    with st.form("process_form"):
        sender = st.text_input("발신자", "test@example.com")
        subject = st.text_input("제목", "")
        body = st.text_area("본문", "", height=150)
        submitted = st.form_submit_button("처리 시작")

    if submitted and subject and body:
        with st.spinner("AI가 이메일을 분석 중..."):
            import time
            import uuid
            from datetime import datetime
            from src.graph.workflow import build_workflow_auto
            from src.db.repository import save_result

            workflow = build_workflow_auto()
            email_id = f"dash_{uuid.uuid4().hex[:8]}"

            start = time.time()
            config = {"configurable": {"thread_id": email_id}}
            state = workflow.invoke(
                {
                    "email_id": email_id,
                    "sender": sender,
                    "subject": subject,
                    "body": body,
                    "received_at": datetime.now().isoformat(),
                    "revision_count": 0,
                    "processing_log": [],
                },
                config=config,
            )
            elapsed = int((time.time() - start) * 1000)
            save_result(state, processing_time_ms=elapsed)

        st.success(f"처리 완료! ({elapsed}ms)")
        st.json({
            "category": state.get("category"),
            "priority": state.get("priority"),
            "sentiment": state.get("sentiment"),
            "review_decision": state.get("review_decision"),
        })
        if state.get("final_response"):
            st.text_area("생성된 응답", state["final_response"], height=200)
        st.rerun()


if __name__ == "__main__":
    main()

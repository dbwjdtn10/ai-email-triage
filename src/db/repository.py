"""데이터베이스 CRUD 함수"""

import json
from typing import Optional

from src.db.database import get_connection, init_db
from src.graph.state import EmailState


def save_result(state: EmailState, processing_time_ms: int = 0):
    """처리 결과를 DB에 저장"""
    init_db()
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO processing_records
            (email_id, sender, subject, body, category, category_confidence,
             priority, sentiment, sentiment_intensity, draft_response,
             final_response, review_decision, human_approved, revision_count,
             processing_log, processing_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                state["email_id"],
                state["sender"],
                state["subject"],
                state["body"],
                state["category"],
                state.get("category_confidence", 0.0),
                state["priority"],
                state.get("sentiment", "neutral"),
                state.get("sentiment_intensity", 0.0),
                state.get("draft_response"),
                state.get("final_response"),
                state.get("review_decision"),
                state.get("human_approved"),
                state.get("revision_count", 0),
                json.dumps(state.get("processing_log", []), ensure_ascii=False),
                processing_time_ms,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_history(
    limit: int = 10,
    priority: Optional[str] = None,
    category: Optional[str] = None,
) -> list[dict]:
    """처리 이력 조회"""
    init_db()
    conn = get_connection()
    try:
        query = "SELECT * FROM processing_records WHERE 1=1"
        params = []

        if priority:
            query += " AND priority = ?"
            params.append(priority)
        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_stats() -> dict:
    """처리 통계 조회"""
    init_db()
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM processing_records").fetchone()[0]

        category_stats = dict(
            conn.execute(
                "SELECT category, COUNT(*) FROM processing_records GROUP BY category"
            ).fetchall()
        )

        priority_stats = dict(
            conn.execute(
                "SELECT priority, COUNT(*) FROM processing_records GROUP BY priority"
            ).fetchall()
        )

        sentiment_stats = dict(
            conn.execute(
                "SELECT sentiment, COUNT(*) FROM processing_records GROUP BY sentiment"
            ).fetchall()
        )

        avg_time = conn.execute(
            "SELECT AVG(processing_time_ms) FROM processing_records WHERE processing_time_ms > 0"
        ).fetchone()[0]

        return {
            "total": total,
            "by_category": category_stats,
            "by_priority": priority_stats,
            "by_sentiment": sentiment_stats,
            "avg_processing_time_ms": round(avg_time or 0, 1),
        }
    finally:
        conn.close()

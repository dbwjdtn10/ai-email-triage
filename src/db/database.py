"""SQLite 데이터베이스 연결 및 초기화"""

import sqlite3

from src.utils.config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """데이터베이스 테이블 초기화"""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS processing_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id TEXT NOT NULL UNIQUE,
            sender TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT,
            category TEXT NOT NULL,
            category_confidence REAL,
            priority TEXT NOT NULL,
            sentiment TEXT,
            sentiment_intensity REAL,
            draft_response TEXT,
            final_response TEXT,
            review_decision TEXT,
            human_approved BOOLEAN,
            revision_count INTEGER DEFAULT 0,
            processing_log TEXT,
            processing_time_ms INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_priority ON processing_records(priority)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_category ON processing_records(category)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_created_at ON processing_records(created_at)
    """)
    conn.commit()
    conn.close()

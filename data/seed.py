"""샘플 데이터를 DB에 시드하는 스크립트"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.database import init_db
from src.db.repository import save_result


def seed():
    init_db()

    # 미리 분석된 결과로 DB에 시드 (데모용)
    sample_results = [
        {
            "email_id": "seed_001",
            "sender": "kim@company.com",
            "subject": "긴급: 결제 시스템 오류",
            "body": "결제 시스템이 작동하지 않습니다.",
            "category": "complaint",
            "category_confidence": 0.95,
            "priority": "high",
            "sentiment": "urgent",
            "sentiment_intensity": 0.9,
            "draft_response": "안녕하세요, 결제 시스템 오류로 불편을 드려 죄송합니다. 현재 기술팀에서 긴급 대응 중입니다.",
            "final_response": "안녕하세요, 결제 시스템 오류로 불편을 드려 죄송합니다. 현재 기술팀에서 긴급 대응 중이며, 30분 내 복구 예정입니다.",
            "review_decision": "approved",
            "human_approved": True,
            "revision_count": 0,
            "processing_log": ["[분류] complaint", "[감정] urgent", "[우선순위] HIGH", "[응답생성] 완료", "[검토] APPROVED"],
        },
        {
            "email_id": "seed_002",
            "sender": "lee@customer.com",
            "subject": "제품 기능 제안",
            "body": "CSV 내보내기 기능을 추가해주세요.",
            "category": "suggestion",
            "category_confidence": 0.90,
            "priority": "medium",
            "sentiment": "positive",
            "sentiment_intensity": 0.6,
            "draft_response": "소중한 제안 감사합니다. CSV 내보내기 기능을 검토하겠습니다.",
            "final_response": "소중한 제안 감사합니다. CSV 내보내기 기능을 다음 분기 로드맵에 반영하여 검토하겠습니다.",
            "review_decision": "approved",
            "revision_count": 0,
            "processing_log": ["[분류] suggestion", "[감정] positive", "[우선순위] MEDIUM", "[응답생성] 완료", "[검토] APPROVED"],
        },
        {
            "email_id": "seed_003",
            "sender": "promo@spam.com",
            "subject": "축하합니다! 당첨!",
            "body": "지금 클릭하세요!",
            "category": "spam",
            "category_confidence": 0.99,
            "priority": "low",
            "sentiment": "neutral",
            "sentiment_intensity": 0.1,
            "review_decision": None,
            "revision_count": 0,
            "processing_log": ["[분류] spam", "[스팸] 처리 종료"],
        },
    ]

    for result in sample_results:
        result.setdefault("received_at", "2025-03-10T09:00:00Z")
        save_result(result, processing_time_ms=1500)

    print(f"시드 완료: {len(sample_results)}건")


if __name__ == "__main__":
    seed()

# API Reference

## Base URL
```
http://localhost:8000/api/v1
```

## Endpoints

### POST /process
단건 이메일을 처리합니다.

**Request Body:**
```json
{
  "sender": "kim@company.com",
  "subject": "긴급: 결제 오류",
  "body": "결제 시스템이 작동하지 않습니다.",
  "email_id": "optional_custom_id"
}
```

**Response:**
```json
{
  "email_id": "api_a1b2c3d4",
  "category": "complaint",
  "category_confidence": 0.95,
  "priority": "high",
  "priority_reason": "결제 시스템 장애로 즉시 대응 필요",
  "sentiment": "urgent",
  "sentiment_intensity": 0.9,
  "draft_response": "안녕하세요, 불편을 드려 죄송합니다...",
  "final_response": "안녕하세요, 불편을 드려 죄송합니다...",
  "review_decision": "approved",
  "processing_time_ms": 3200,
  "processing_log": [
    "[분류] complaint (신뢰도: 0.95)",
    "[감정분석] urgent (강도: 0.90)",
    "[우선순위] HIGH",
    "[응답생성] 완료",
    "[검토] APPROVED"
  ]
}
```

### POST /batch
여러 이메일을 한 번에 처리합니다.

**Request Body:** `ProcessRequest[]` 배열

**Response:**
```json
{
  "processed": 5,
  "results": [...]
}
```

### GET /history
처리 이력을 조회합니다.

**Query Parameters:**
| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|-------|------|
| limit | int | 10 | 조회 건수 |
| priority | string | null | 우선순위 필터 (high/medium/low) |
| category | string | null | 카테고리 필터 |

### GET /stats
처리 통계를 조회합니다.

**Response:**
```json
{
  "total": 50,
  "by_category": {"complaint": 15, "inquiry": 20, "spam": 5, ...},
  "by_priority": {"high": 10, "medium": 25, "low": 15},
  "by_sentiment": {"negative": 12, "neutral": 20, ...},
  "avg_processing_time_ms": 2800.5
}
```

### GET /health
서비스 헬스체크

**Response:**
```json
{"status": "ok", "service": "ai-email-triage"}
```

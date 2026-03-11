"""API 엔드포인트 정의"""

import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.db.repository import get_history, get_stats, save_result
from src.graph.workflow import build_workflow_auto

router = APIRouter()

# 워크플로우 싱글턴
_workflow = None


def _get_workflow():
    global _workflow
    if _workflow is None:
        _workflow = build_workflow_auto()
    return _workflow


class ProcessRequest(BaseModel):
    sender: str
    subject: str
    body: str
    email_id: Optional[str] = None


class ProcessResponse(BaseModel):
    email_id: str
    category: str
    category_confidence: float
    priority: str
    priority_reason: str
    sentiment: str
    sentiment_intensity: float
    draft_response: Optional[str] = None
    final_response: Optional[str] = None
    review_decision: Optional[str] = None
    processing_time_ms: int
    processing_log: list[str]


@router.post("/process", response_model=ProcessResponse)
def process_email(req: ProcessRequest):
    """단건 이메일 처리"""
    import uuid
    from datetime import datetime

    email_id = req.email_id or f"api_{uuid.uuid4().hex[:8]}"

    initial_state = {
        "email_id": email_id,
        "sender": req.sender,
        "subject": req.subject,
        "body": req.body,
        "received_at": datetime.now().isoformat(),
        "revision_count": 0,
        "processing_log": [],
    }

    start = time.time()
    try:
        workflow = _get_workflow()
        config = {"configurable": {"thread_id": email_id}}
        state = workflow.invoke(initial_state, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 실패: {str(e)}")

    elapsed = int((time.time() - start) * 1000)
    save_result(state, processing_time_ms=elapsed)

    return ProcessResponse(
        email_id=email_id,
        category=state.get("category", "other"),
        category_confidence=state.get("category_confidence", 0.0),
        priority=state.get("priority", "low"),
        priority_reason=state.get("priority_reason", ""),
        sentiment=state.get("sentiment", "neutral"),
        sentiment_intensity=state.get("sentiment_intensity", 0.0),
        draft_response=state.get("draft_response"),
        final_response=state.get("final_response"),
        review_decision=state.get("review_decision"),
        processing_time_ms=elapsed,
        processing_log=state.get("processing_log", []),
    )


@router.post("/batch")
def batch_process(emails: list[ProcessRequest]):
    """배치 이메일 처리"""
    results = []
    for email in emails:
        try:
            result = process_email(email)
            results.append(result)
        except Exception as e:
            results.append({"email_id": email.email_id, "error": str(e)})
    return {"processed": len(results), "results": results}


@router.get("/history")
def get_processing_history(
    limit: int = 10,
    priority: Optional[str] = None,
    category: Optional[str] = None,
):
    """처리 이력 조회"""
    return get_history(limit=limit, priority=priority, category=category)


@router.get("/stats")
def get_processing_stats():
    """처리 통계"""
    return get_stats()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "ai-email-triage"}

"""API 엔드포인트 정의 - Rate Limiting + 병렬 배치 + 구조화된 에러"""

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.auth import verify_api_key
from src.api.metrics import record_email_processed
from src.db.repository import get_history, get_stats, save_result
from src.graph.workflow import build_workflow_auto
from src.models.api import BatchResponse, BatchResult, ErrorResponse, TokenUsageResponse
from src.utils.config import get_settings

router = APIRouter(dependencies=[Depends(verify_api_key)])
limiter = Limiter(key_func=get_remote_address)

# 워크플로우 싱글턴
_workflow = None


def _get_workflow():
    global _workflow
    if _workflow is None:
        _workflow = build_workflow_auto()
    return _workflow


# ── 요청/응답 스키마 ──


class ProcessRequest(BaseModel):
    sender: str = Field(min_length=1, description="발신자 이메일")
    subject: str = Field(min_length=1, description="이메일 제목")
    body: str = Field(min_length=1, description="이메일 본문")
    email_id: Optional[str] = Field(
        default=None, description="이메일 고유 ID (미입력 시 자동 생성)"
    )


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
    token_usage: Optional[TokenUsageResponse] = None


# ── 내부 처리 함수 ──


def _process_single(req: ProcessRequest) -> dict:
    """단건 이메일 처리 (내부용 - 배치에서도 호출)"""
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
    workflow = _get_workflow()
    config = {"configurable": {"thread_id": email_id}}
    state = workflow.invoke(initial_state, config=config)
    elapsed = int((time.time() - start) * 1000)

    save_result(state, processing_time_ms=elapsed)
    record_email_processed(state, elapsed)

    token_usage = state.get("token_usage")

    return {
        "email_id": email_id,
        "category": state.get("category", "other"),
        "category_confidence": state.get("category_confidence", 0.0),
        "priority": state.get("priority", "low"),
        "priority_reason": state.get("priority_reason", ""),
        "sentiment": state.get("sentiment", "neutral"),
        "sentiment_intensity": state.get("sentiment_intensity", 0.0),
        "draft_response": state.get("draft_response"),
        "final_response": state.get("final_response"),
        "review_decision": state.get("review_decision"),
        "processing_time_ms": elapsed,
        "processing_log": state.get("processing_log", []),
        "token_usage": token_usage,
    }


# ── 엔드포인트 ──


@router.post(
    "/process",
    response_model=ProcessResponse,
    responses={429: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
@limiter.limit(get_settings().rate_limit_process)
def process_email(req: ProcessRequest, request: Request):
    """단건 이메일 처리"""
    try:
        return _process_single(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 실패: {str(e)}")


@router.post(
    "/batch",
    response_model=BatchResponse,
    responses={429: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
@limiter.limit(get_settings().rate_limit_batch)
def batch_process(emails: list[ProcessRequest], request: Request):
    """배치 이메일 처리 (ThreadPoolExecutor로 병렬 실행)"""
    settings = get_settings()
    results: list[BatchResult] = []

    with ThreadPoolExecutor(max_workers=settings.max_concurrent_emails) as executor:
        future_to_email = {
            executor.submit(_process_single, email): email for email in emails
        }
        for future in as_completed(future_to_email):
            email = future_to_email[future]
            email_id = email.email_id or "unknown"
            try:
                result = future.result()
                results.append(BatchResult(
                    email_id=result["email_id"],
                    status="success",
                    result=result,
                ))
            except Exception as e:
                results.append(BatchResult(
                    email_id=email_id,
                    status="error",
                    error=str(e),
                ))

    succeeded = sum(1 for r in results if r.status == "success")
    return BatchResponse(
        total=len(results),
        succeeded=succeeded,
        failed=len(results) - succeeded,
        results=results,
    )


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
    """처리 통계 (토큰 사용량 포함)"""
    return get_stats()


@router.get("/health")
def health_check():
    """간략한 헬스 체크 (로드밸런서용)"""
    return {"status": "ok", "service": "ai-email-triage", "version": "0.2.0"}


@router.get("/health/detail")
def health_check_detail():
    """상세 헬스 체크 - DB, LLM 등 의존성 상태 확인"""
    import sqlite3
    import time

    checks: dict = {}
    overall = "ok"

    # DB 연결 체크
    try:
        start = time.time()
        conn = sqlite3.connect(str(get_settings().database_path))
        conn.execute("SELECT 1")
        conn.close()
        checks["database"] = {
            "status": "ok",
            "latency_ms": round((time.time() - start) * 1000, 1),
        }
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}
        overall = "degraded"

    # LLM 가용성 체크 (API Key 존재 여부로 판단)
    import os

    openai_key = bool(os.getenv("OPENAI_API_KEY"))
    anthropic_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    checks["llm"] = {
        "status": "ok" if (openai_key or anthropic_key) else "error",
        "primary_configured": openai_key,
        "fallback_configured": anthropic_key,
    }
    if not openai_key and not anthropic_key:
        overall = "degraded"

    # 워크플로우 체크
    try:
        wf = _get_workflow()
        checks["workflow"] = {
            "status": "ok",
            "nodes": list(wf.get_graph().nodes.keys()),
        }
    except Exception as e:
        checks["workflow"] = {"status": "error", "detail": str(e)}
        overall = "degraded"

    return {
        "status": overall,
        "service": "ai-email-triage",
        "version": "0.2.0",
        "checks": checks,
    }

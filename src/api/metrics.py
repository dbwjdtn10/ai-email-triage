"""Prometheus 메트릭 - 처리량, 레이턴시, 에러율 모니터링"""

from prometheus_client import Counter, Histogram, Info

# ── 서비스 정보 ──
SERVICE_INFO = Info("email_triage", "AI Email Triage 서비스 정보")
SERVICE_INFO.info({"version": "0.2.0", "framework": "langgraph"})

# ── 요청 메트릭 ──
REQUESTS_TOTAL = Counter(
    "email_triage_requests_total",
    "총 API 요청 수",
    ["method", "endpoint", "status"],
)

# ── 이메일 처리 메트릭 ──
EMAILS_PROCESSED = Counter(
    "email_triage_emails_processed_total",
    "처리된 이메일 총 수",
    ["category", "priority", "sentiment"],
)

PROCESSING_DURATION = Histogram(
    "email_triage_processing_duration_seconds",
    "이메일 처리 소요 시간 (초)",
    ["priority"],
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0],
)

# ── LLM 메트릭 ──
LLM_TOKENS_TOTAL = Counter(
    "email_triage_llm_tokens_total",
    "LLM 사용 토큰 총 수",
    ["type"],  # prompt, completion
)

LLM_ERRORS = Counter(
    "email_triage_llm_errors_total",
    "LLM 호출 에러 수",
    ["error_type"],
)

LLM_RETRIES = Counter(
    "email_triage_llm_retries_total",
    "LLM 재시도 횟수",
)


def record_email_processed(state: dict, processing_time_ms: int):
    """이메일 처리 완료 시 메트릭 기록"""
    category = state.get("category", "unknown")
    priority = state.get("priority", "unknown")
    sentiment = state.get("sentiment", "unknown")

    EMAILS_PROCESSED.labels(
        category=category, priority=priority, sentiment=sentiment,
    ).inc()

    PROCESSING_DURATION.labels(priority=priority).observe(
        processing_time_ms / 1000.0
    )

    token_usage = state.get("token_usage") or {}
    if token_usage.get("prompt_tokens"):
        LLM_TOKENS_TOTAL.labels(type="prompt").inc(token_usage["prompt_tokens"])
    if token_usage.get("completion_tokens"):
        LLM_TOKENS_TOTAL.labels(type="completion").inc(token_usage["completion_tokens"])

"""FastAPI 서버 - 이메일 트리아지 REST API (Rate Limiting + Middleware + Metrics)"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api.metrics import REQUESTS_TOTAL
from src.api.middleware import RequestTrackingMiddleware
from src.api.routes import router
from src.db.database import init_db
from src.models.api import ErrorResponse

# Rate Limiter 인스턴스 (routes.py에서도 참조)
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI Email Triage API",
    description="LangGraph 기반 멀티 에이전트 이메일 트리아지 시스템",
    version="0.2.0",
    lifespan=lifespan,
)

# ── Rate Limiter 등록 ──
app.state.limiter = limiter


# ── Prometheus 메트릭 엔드포인트 ──
@app.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus 스크래핑용 메트릭 엔드포인트"""
    return Response(
        content=generate_latest(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ── 에러 핸들러 ──
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    REQUESTS_TOTAL.labels(
        method=request.method, endpoint=request.url.path, status="429",
    ).inc()
    return JSONResponse(
        status_code=429,
        content=ErrorResponse(
            code="RATE_LIMITED",
            message="요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
            detail=str(exc.detail),
            request_id=request.headers.get("X-Request-ID"),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    REQUESTS_TOTAL.labels(
        method=request.method, endpoint=request.url.path, status="500",
    ).inc()
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            code="INTERNAL_ERROR",
            message="서버 내부 오류가 발생했습니다.",
            detail=str(exc),
            request_id=request.headers.get("X-Request-ID"),
        ).model_dump(),
    )


# ── 미들웨어 (등록 순서 = 실행 역순) ──
app.add_middleware(RequestTrackingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

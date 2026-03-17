"""요청 추적 미들웨어 - Correlation ID + 처리 시간 측정"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.utils.logger import get_logger

logger = get_logger("api.middleware")


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    각 요청에 고유 추적 ID를 부여하고 처리 시간을 측정하는 미들웨어.

    - X-Request-ID: 클라이언트가 보내면 그대로 사용, 없으면 서버에서 생성
    - X-Process-Time: 요청 처리 소요 시간 (초)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
        start_time = time.perf_counter()

        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - 요청 시작"
        )

        response: Response = await call_next(request)

        process_time = time.perf_counter() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}"

        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"{response.status_code} ({process_time:.3f}s)"
        )

        return response

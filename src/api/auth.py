"""API Key 인증 - Bearer 토큰 기반 접근 제어"""

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from src.utils.config import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(_api_key_header)) -> str | None:
    """
    API Key 검증 의존성.

    - API_KEY 설정이 빈 문자열이면 인증을 건너뜀 (개발 환경)
    - 설정되어 있으면 X-API-Key 헤더와 비교하여 인증
    """
    settings = get_settings()

    # 인증 비활성화 (개발 모드)
    if not settings.api_key:
        return None

    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=401,
            detail="유효하지 않은 API Key입니다.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key

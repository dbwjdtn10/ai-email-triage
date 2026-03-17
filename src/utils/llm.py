"""LLM 팩토리 - Primary + Fallback 체인 + 응답 캐싱"""

from langchain_anthropic import ChatAnthropic
from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.utils.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# LLM 응답 캐싱: 동일 프롬프트+파라미터 조합에 대해 LLM 재호출 방지 → 비용 절감
_cache_initialized = False


def _init_cache():
    global _cache_initialized
    if not _cache_initialized:
        set_llm_cache(InMemoryCache())
        _cache_initialized = True
        logger.info("LLM 응답 캐시 활성화 (InMemoryCache)")


def _create_llm(model: str) -> BaseChatModel:
    settings = get_settings()
    if model.startswith("claude") or model.startswith("anthropic"):
        return ChatAnthropic(
            model=model,
            temperature=settings.llm_temperature,
            max_retries=settings.llm_max_retries,
        )
    return ChatOpenAI(
        model=model,
        temperature=settings.llm_temperature,
        max_retries=settings.llm_max_retries,
    )


def get_primary_llm() -> BaseChatModel:
    return _create_llm(get_settings().primary_llm)


def get_fallback_llm() -> BaseChatModel:
    return _create_llm(get_settings().fallback_llm)


def get_llm_with_fallback() -> BaseChatModel:
    """Primary LLM 실패 시 Fallback LLM으로 자동 전환 + 캐싱 활성화"""
    _init_cache()
    primary = get_primary_llm()
    fallback = get_fallback_llm()
    return primary.with_fallbacks([fallback])

"""LLM 팩토리 - Primary + Fallback 체인 구성"""

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from .config import FALLBACK_LLM, LLM_MAX_RETRIES, LLM_TEMPERATURE, PRIMARY_LLM


def _create_llm(model: str) -> BaseChatModel:
    if model.startswith("claude") or model.startswith("anthropic"):
        return ChatAnthropic(
            model=model,
            temperature=LLM_TEMPERATURE,
            max_retries=LLM_MAX_RETRIES,
        )
    return ChatOpenAI(
        model=model,
        temperature=LLM_TEMPERATURE,
        max_retries=LLM_MAX_RETRIES,
    )


def get_primary_llm() -> BaseChatModel:
    return _create_llm(PRIMARY_LLM)


def get_fallback_llm() -> BaseChatModel:
    return _create_llm(FALLBACK_LLM)


def get_llm_with_fallback() -> BaseChatModel:
    """Primary LLM 실패 시 Fallback LLM으로 자동 전환"""
    primary = get_primary_llm()
    fallback = get_fallback_llm()
    return primary.with_fallbacks([fallback])

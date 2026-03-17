"""LangGraph 노드 함수들 - 각 에이전트를 노드로 래핑 (retry + 토큰 추적 포함)"""

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.agents.classifier import ClassifierAgent
from src.agents.draft_generator import DraftGeneratorAgent
from src.agents.prioritizer import PrioritizerAgent
from src.agents.reviewer import ReviewerAgent
from src.agents.sentiment import SentimentAgent
from src.graph.state import EmailState
from src.utils.callbacks import TokenUsageCallbackHandler
from src.utils.llm import get_llm_with_fallback
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 에이전트 인스턴스 (lazy init)
_agents: dict = {}
_token_handler: TokenUsageCallbackHandler | None = None


def _get_agents() -> dict:
    if not _agents:
        llm = get_llm_with_fallback()
        _agents["classifier"] = ClassifierAgent(llm)
        _agents["prioritizer"] = PrioritizerAgent(llm)
        _agents["sentiment"] = SentimentAgent(llm)
        _agents["draft_generator"] = DraftGeneratorAgent(llm)
        _agents["reviewer"] = ReviewerAgent(llm)
    return _agents


def _get_token_handler() -> TokenUsageCallbackHandler:
    global _token_handler
    if _token_handler is None:
        _token_handler = TokenUsageCallbackHandler()
    return _token_handler


def _log_retry(retry_state):
    """tenacity 재시도 시 로깅"""
    logger.warning(
        f"LLM 호출 재시도 ({retry_state.attempt_number}회차) - "
        f"에러: {retry_state.outcome.exception()}"
    )


# 재시도 데코레이터: LLM API 일시적 장애(rate limit, timeout) 대응
_llm_retry = retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    before_sleep=_log_retry,
    reraise=True,
)


@_llm_retry
def classify(state: EmailState) -> dict:
    logger.info(f"[분류] 이메일 처리 시작: {state['subject']}")
    handler = _get_token_handler()
    result = _get_agents()["classifier"].run(state)
    result["token_usage"] = handler.get_usage_snapshot()
    return result


@_llm_retry
def analyze_sentiment(state: EmailState) -> dict:
    logger.info(f"[감정분석] 이메일 분석: {state['subject']}")
    handler = _get_token_handler()
    result = _get_agents()["sentiment"].run(state)
    result["token_usage"] = handler.get_usage_snapshot()
    return result


@_llm_retry
def prioritize(state: EmailState) -> dict:
    logger.info(f"[우선순위] 카테고리={state['category']}, 감정={state.get('sentiment')}")
    handler = _get_token_handler()
    result = _get_agents()["prioritizer"].run(state)
    result["token_usage"] = handler.get_usage_snapshot()
    return result


@_llm_retry
def generate_draft(state: EmailState) -> dict:
    revision = state.get("revision_count", 0)
    logger.info(f"[응답생성] 수정횟수={revision}")
    handler = _get_token_handler()
    result = _get_agents()["draft_generator"].run(state)
    result["token_usage"] = handler.get_usage_snapshot()
    return result


@_llm_retry
def review_draft(state: EmailState) -> dict:
    logger.info("[검토] 응답 초안 검토 시작")
    handler = _get_token_handler()
    result = _get_agents()["reviewer"].run(state)
    result["token_usage"] = handler.get_usage_snapshot()
    return result


def send_alert(state: EmailState) -> dict:
    """HIGH 우선순위 알림 전송 (실제 연동 시 Slack/Email 등)"""
    logger.info(f"[알림] HIGH 우선순위 이메일 감지: {state['subject']}")
    return {
        "processing_log": [
            f"[알림] HIGH 우선순위 알림 전송 완료 - {state['subject']}"
        ],
    }


def mark_spam(state: EmailState) -> dict:
    """스팸 처리"""
    logger.info(f"[스팸] 스팸 메일 처리: {state['subject']}")
    return {
        "final_response": None,
        "processing_log": ["[스팸] 스팸으로 분류되어 처리 종료"],
    }

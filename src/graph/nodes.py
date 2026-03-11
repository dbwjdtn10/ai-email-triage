"""LangGraph 노드 함수들 - 각 에이전트를 노드로 래핑"""

from src.agents.classifier import ClassifierAgent
from src.agents.draft_generator import DraftGeneratorAgent
from src.agents.prioritizer import PrioritizerAgent
from src.agents.reviewer import ReviewerAgent
from src.agents.sentiment import SentimentAgent
from src.graph.state import EmailState
from src.utils.llm import get_llm_with_fallback
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 에이전트 인스턴스 (lazy init)
_agents: dict = {}


def _get_agents() -> dict:
    if not _agents:
        llm = get_llm_with_fallback()
        _agents["classifier"] = ClassifierAgent(llm)
        _agents["prioritizer"] = PrioritizerAgent(llm)
        _agents["sentiment"] = SentimentAgent(llm)
        _agents["draft_generator"] = DraftGeneratorAgent(llm)
        _agents["reviewer"] = ReviewerAgent(llm)
    return _agents


def classify(state: EmailState) -> dict:
    logger.info(f"[분류] 이메일 처리 시작: {state['subject']}")
    return _get_agents()["classifier"].run(state)


def analyze_sentiment(state: EmailState) -> dict:
    logger.info(f"[감정분석] 이메일 분석: {state['subject']}")
    return _get_agents()["sentiment"].run(state)


def prioritize(state: EmailState) -> dict:
    logger.info(f"[우선순위] 카테고리={state['category']}, 감정={state.get('sentiment')}")
    return _get_agents()["prioritizer"].run(state)


def generate_draft(state: EmailState) -> dict:
    revision = state.get("revision_count", 0)
    logger.info(f"[응답생성] 수정횟수={revision}")
    return _get_agents()["draft_generator"].run(state)


def review_draft(state: EmailState) -> dict:
    logger.info("[검토] 응답 초안 검토 시작")
    return _get_agents()["reviewer"].run(state)


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

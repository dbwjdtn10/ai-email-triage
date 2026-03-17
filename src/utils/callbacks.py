"""LLM 토큰 사용량 & 비용 추적 콜백"""

import threading
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

# 모델별 1K 토큰당 비용 (USD)
MODEL_COSTS = {
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "gpt-4o": {"prompt": 0.0025, "completion": 0.01},
    "claude-haiku-4-5-20251001": {"prompt": 0.0008, "completion": 0.004},
}


class TokenUsageCallbackHandler(BaseCallbackHandler):
    """LLM 호출마다 토큰 사용량과 비용을 누적 추적하는 콜백 핸들러"""

    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.estimated_cost = 0.0
        self.llm_calls = 0

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """LLM 호출 완료 시 토큰 사용량 집계"""
        usage = {}
        if response.llm_output:
            usage = response.llm_output.get("token_usage", {})

        with self._lock:
            prompt = usage.get("prompt_tokens", 0)
            completion = usage.get("completion_tokens", 0)
            total = usage.get("total_tokens", prompt + completion)

            self.prompt_tokens += prompt
            self.completion_tokens += completion
            self.total_tokens += total
            self.llm_calls += 1

            # 비용 계산
            model = (response.llm_output or {}).get("model_name", "")
            costs = MODEL_COSTS.get(model, {"prompt": 0.0003, "completion": 0.001})
            self.estimated_cost += (
                (prompt / 1000) * costs["prompt"]
                + (completion / 1000) * costs["completion"]
            )

    def get_usage_snapshot(self) -> dict:
        """현재까지의 사용량 스냅샷 반환"""
        with self._lock:
            return {
                "total_tokens": self.total_tokens,
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "estimated_cost_usd": round(self.estimated_cost, 6),
                "llm_calls": self.llm_calls,
            }

    def reset(self) -> None:
        """사용량 카운터 초기화"""
        with self._lock:
            self.total_tokens = 0
            self.prompt_tokens = 0
            self.completion_tokens = 0
            self.estimated_cost = 0.0
            self.llm_calls = 0

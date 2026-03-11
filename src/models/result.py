"""DB에 저장할 처리 이력 모델"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProcessingRecord(BaseModel):
    id: Optional[int] = None
    email_id: str
    sender: str
    subject: str
    category: str
    category_confidence: float
    priority: str
    sentiment: str
    sentiment_intensity: float
    draft_response: Optional[str] = None
    final_response: Optional[str] = None
    review_decision: Optional[str] = None
    human_approved: Optional[bool] = None
    revision_count: int = 0
    processing_log: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    processing_time_ms: Optional[int] = None

"""Pydantic request and response models for the HTTP/SSE API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from core.modes import ReviewMode


class ReviewRequest(BaseModel):
    code: str = Field(min_length=1)
    language: Optional[str] = None
    mode: ReviewMode = ReviewMode.STANDARD
    max_rounds: Optional[int] = Field(default=None, ge=1, le=10)
    run_fixer: bool = True


class DebateMessageOut(BaseModel):
    agent: str
    round_number: int
    content: str
    is_initial_review: bool


class ReviewSummary(BaseModel):
    id: str
    language: Optional[str]
    mode: str
    rounds: int
    status: str
    score: Optional[int]
    winner: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    code_preview: str


class ReviewDetail(ReviewSummary):
    code: str
    messages: list[DebateMessageOut]
    verdict: Optional[dict] = None
    fix: Optional[dict] = None
    error: Optional[str] = None

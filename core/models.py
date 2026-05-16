from typing import Literal, Optional
from pydantic import BaseModel, Field


Category = Literal["BUG", "SECURITY", "EDGE_CASE", "PERF", "DESIGN", "STYLE"]
Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
AgentName = Literal["CRITIC", "ADVOCATE"]


class ReviewItem(BaseModel):
    category: Category
    severity: Severity
    line_number: Optional[int] = Field(
        default=None,
        description="1-indexed line number the issue refers to, if applicable.",
    )
    issue: str = Field(description="Concrete description of what's wrong.")
    suggestion: str = Field(description="Specific action to take, not vague advice.")


class CriticReview(BaseModel):
    summary: str = Field(description="1-2 sentence overall verdict.")
    items: list[ReviewItem] = Field(default_factory=list)


class DebateMessage(BaseModel):
    agent: AgentName
    round_number: int = Field(description="1-indexed round in which this message was spoken.")
    content: str = Field(
        description="Prose body of the turn. For the initial review only, "
        "this is a JSON-serialized CriticReview."
    )
    is_initial_review: bool = Field(
        default=False,
        description="True only for the Critic's structured opening review.",
    )


class DebateState(BaseModel):
    code: str
    language: Optional[str] = None
    transcript: list[DebateMessage] = Field(default_factory=list)
    max_rounds: int = 3

    def get_initial_review(self) -> Optional[CriticReview]:
        """Return the parsed initial review if it has been recorded, else None."""
        if self.transcript and self.transcript[0].is_initial_review:
            return CriticReview.model_validate_json(self.transcript[0].content)
        return None

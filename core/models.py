from typing import Literal, Optional
from pydantic import BaseModel, Field


Category = Literal["BUG", "SECURITY", "EDGE_CASE", "PERF", "DESIGN", "STYLE"]
Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


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

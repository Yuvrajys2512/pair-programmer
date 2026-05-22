"""SQLAlchemy ORM models for persisted reviews."""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from web.db import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(32))
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    rounds: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    score: Mapped[Optional[int]] = mapped_column(Integer)
    winner: Mapped[Optional[str]] = mapped_column(String(16))
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    messages: Mapped[list["DebateMessageRow"]] = relationship(
        back_populates="review", cascade="all, delete-orphan", order_by="DebateMessageRow.position",
    )
    verdict: Mapped[Optional["VerdictRow"]] = relationship(
        back_populates="review", cascade="all, delete-orphan", uselist=False,
    )
    fix: Mapped[Optional["FixRow"]] = relationship(
        back_populates="review", cascade="all, delete-orphan", uselist=False,
    )


class DebateMessageRow(Base):
    __tablename__ = "debate_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    agent: Mapped[str] = mapped_column(String(16), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_initial_review: Mapped[bool] = mapped_column(default=False)

    review: Mapped[Review] = relationship(back_populates="messages")


class VerdictRow(Base):
    __tablename__ = "verdicts"

    review_id: Mapped[str] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE"), primary_key=True,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    winner: Mapped[str] = mapped_column(String(16), nullable=False)
    winner_reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    critic_wins: Mapped[list] = mapped_column(JSON, default=list)
    advocate_wins: Mapped[list] = mapped_column(JSON, default=list)
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    action_items: Mapped[list] = mapped_column(JSON, default=list)

    review: Mapped[Review] = relationship(back_populates="verdict")


class FixRow(Base):
    __tablename__ = "fixes"

    review_id: Mapped[str] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE"), primary_key=True,
    )
    fixed_code: Mapped[str] = mapped_column(Text, nullable=False)
    changes_made: Mapped[bool] = mapped_column(default=False)
    changelog: Mapped[list] = mapped_column(JSON, default=list)

    review: Mapped[Review] = relationship(back_populates="fix")

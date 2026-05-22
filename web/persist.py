"""Helpers to save and load reviews from the database."""

from datetime import datetime
from typing import Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from core.models import DebateMessage, FixerResult, Verdict
from web.storage import DebateMessageRow, FixRow, Review, VerdictRow


def create_review(
    db: Session, review_id: str, code: str, language: Optional[str], mode: str, rounds: int,
) -> Review:
    row = Review(
        id=review_id, code=code, language=language, mode=mode, rounds=rounds, status="pending",
    )
    db.add(row)
    db.commit()
    return row


def persist_message(db: Session, review_id: str, position: int, msg: DebateMessage) -> None:
    db.add(DebateMessageRow(
        review_id=review_id, position=position,
        agent=msg.agent, round_number=msg.round_number,
        content=msg.content, is_initial_review=msg.is_initial_review,
    ))
    db.commit()


def persist_verdict(db: Session, review_id: str, verdict: Verdict) -> None:
    db.add(VerdictRow(
        review_id=review_id,
        summary=verdict.summary, score=verdict.score,
        winner=verdict.winner, winner_reasoning=verdict.winner_reasoning,
        critic_wins=list(verdict.critic_wins),
        advocate_wins=list(verdict.advocate_wins),
        strengths=list(verdict.strengths),
        action_items=[ai.model_dump() for ai in verdict.action_items],
    ))
    review = db.get(Review, review_id)
    if review is not None:
        review.score = verdict.score
        review.winner = verdict.winner
    db.commit()


def persist_fix(db: Session, review_id: str, result: FixerResult) -> None:
    db.add(FixRow(
        review_id=review_id,
        fixed_code=result.fixed_code,
        changes_made=result.changes_made,
        changelog=[c.model_dump() for c in result.changelog],
    ))
    db.commit()


def mark_complete(db: Session, review_id: str, error: Optional[str] = None) -> None:
    review = db.get(Review, review_id)
    if review is None:
        return
    review.status = "error" if error else "complete"
    review.error = error
    review.completed_at = datetime.utcnow()
    db.commit()


def list_reviews(db: Session, limit: int = 50) -> list[Review]:
    return list(
        db.query(Review).order_by(desc(Review.created_at)).limit(limit).all()
    )


def get_review(db: Session, review_id: str) -> Optional[Review]:
    return db.get(Review, review_id)

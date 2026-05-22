"""FastAPI app exposing the Pair Programmer pipeline over HTTP/SSE."""

import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.personas import list_personas, validate_persona
from web.api_models import (
    DebateMessageOut, PersonaOut, ReviewDetail, ReviewRequest, ReviewSummary,
)
from web.db import SessionLocal, init_db
from web.persist import create_review, get_review, list_reviews
from web.sse import stream_pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Pair Programmer API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/personas", response_model=list[PersonaOut])
def list_personas_endpoint() -> list[PersonaOut]:
    return [
        PersonaOut(slug=p.slug, name=p.name, description=p.description)
        for p in list_personas()
    ]


@app.post("/api/reviews/stream")
async def post_review_stream(req: ReviewRequest):
    """Create a review and stream the pipeline back as SSE."""
    try:
        persona = validate_persona(req.persona)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    review_id = uuid.uuid4().hex
    # Persist the request up front so the row exists even if the client disconnects.
    with SessionLocal() as db:
        create_review(
            db,
            review_id=review_id,
            code=req.code,
            language=req.language,
            mode=req.mode.value,
            rounds=req.max_rounds or 0,  # filled in on start by sse generator
            persona=persona,
        )
    return StreamingResponse(
        stream_pipeline(
            review_id=review_id,
            code=req.code,
            language=req.language,
            mode=req.mode,
            max_rounds=req.max_rounds,
            run_fixer=req.run_fixer,
            persona=persona,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _to_summary(r) -> ReviewSummary:
    preview = (r.code.strip().splitlines() or [""])[0][:80]
    return ReviewSummary(
        id=r.id, language=r.language, mode=r.mode,
        persona=r.persona, rounds=r.rounds,
        status=r.status, score=r.score, winner=r.winner,
        created_at=r.created_at, completed_at=r.completed_at,
        code_preview=preview,
    )


@app.get("/api/reviews", response_model=list[ReviewSummary])
def list_reviews_endpoint(limit: int = 50, db: Session = Depends(get_db)):
    rows = list_reviews(db, limit=limit)
    return [_to_summary(r) for r in rows]


@app.get("/api/reviews/{review_id}", response_model=ReviewDetail)
def get_review_endpoint(review_id: str, db: Session = Depends(get_db)):
    r = get_review(db, review_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Review not found")

    messages = [
        DebateMessageOut(
            agent=m.agent,
            round_number=m.round_number,
            content=m.content,
            is_initial_review=m.is_initial_review,
        )
        for m in r.messages
    ]

    verdict_dict = None
    if r.verdict is not None:
        v = r.verdict
        verdict_dict = {
            "summary": v.summary, "score": v.score,
            "winner": v.winner, "winner_reasoning": v.winner_reasoning,
            "critic_wins": v.critic_wins, "advocate_wins": v.advocate_wins,
            "strengths": v.strengths, "action_items": v.action_items,
        }

    fix_dict = None
    if r.fix is not None:
        fix_dict = {
            "fixed_code": r.fix.fixed_code,
            "changes_made": r.fix.changes_made,
            "changelog": r.fix.changelog,
            "original_code": r.code,
        }

    preview = (r.code.strip().splitlines() or [""])[0][:80]
    return ReviewDetail(
        id=r.id, language=r.language, mode=r.mode,
        persona=r.persona, rounds=r.rounds,
        status=r.status, score=r.score, winner=r.winner,
        created_at=r.created_at, completed_at=r.completed_at,
        code_preview=preview,
        code=r.code,
        messages=messages,
        verdict=verdict_dict,
        fix=fix_dict,
        error=r.error,
    )

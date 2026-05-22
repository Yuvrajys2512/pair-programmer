"""Async SSE bridge between the synchronous LangGraph pipeline and the HTTP stream.

The graph nodes call a DebateListener synchronously while running in a worker
thread. The listener pushes events into an asyncio.Queue via the running event
loop, and the SSE generator drains the queue and yields server-sent events.

All persistence (messages, verdict, fix, mark_complete) happens inside the worker
thread so the database always reaches a final state — even if the HTTP client
disconnects mid-stream and the async generator is cancelled.
"""

import asyncio
import json
from typing import AsyncIterator, Optional

from core.listener import DebateListener
from core.models import AgentName, DebateMessage
from core.modes import MAX_ROUNDS, ReviewMode
from web.db import SessionLocal
from web.persist import mark_complete, persist_fix, persist_message, persist_verdict


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"


# Sentinel passed through the queue to mark worker-thread completion.
_DONE = object()


class _StreamingListener(DebateListener):
    """Bridges synchronous LangGraph callbacks to an asyncio queue and the DB."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        queue: "asyncio.Queue[object]",
        review_id: str,
    ) -> None:
        self.loop = loop
        self.queue = queue
        self.review_id = review_id
        self._position = 0

    def _push(self, event: dict) -> None:
        asyncio.run_coroutine_threadsafe(self.queue.put(event), self.loop)

    def on_turn_start(self, agent: AgentName, round_number: int, is_initial_review: bool) -> None:
        self._push({
            "type": "turn_start",
            "agent": agent,
            "round": round_number,
            "is_initial": is_initial_review,
        })

    def on_chunk(self, chunk: str) -> None:
        self._push({"type": "chunk", "text": chunk})

    def on_turn_complete(self, message: DebateMessage) -> None:
        self._position += 1
        with SessionLocal() as db:
            persist_message(db, self.review_id, self._position, message)
        self._push({
            "type": "turn_complete",
            "agent": message.agent,
            "round": message.round_number,
            "content": message.content,
            "is_initial": message.is_initial_review,
        })


async def stream_pipeline(
    review_id: str,
    code: str,
    language: Optional[str],
    mode: ReviewMode,
    max_rounds: Optional[int],
    run_fixer: bool,
    persona: Optional[str] = None,
) -> AsyncIterator[str]:
    from core.graph import run_pipeline

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[object] = asyncio.Queue()
    rounds = max_rounds if max_rounds is not None else MAX_ROUNDS[mode]

    listener = _StreamingListener(loop, queue, review_id)

    def push(ev: object) -> None:
        asyncio.run_coroutine_threadsafe(queue.put(ev), loop)

    def run_in_thread() -> None:
        try:
            final = run_pipeline(
                code=code,
                language=language,
                mode=mode,
                max_rounds=rounds,
                run_verdict=True,
                run_fixer=run_fixer,
                listener=listener,
                persona=persona,
            )
            verdict = final.get("verdict")
            fixer_result = final.get("fixer_result")

            # Persist terminal state — guaranteed to run regardless of client.
            with SessionLocal() as db:
                if verdict is not None:
                    persist_verdict(db, review_id, verdict)
                if fixer_result is not None:
                    persist_fix(db, review_id, fixer_result)
                mark_complete(db, review_id)

            if verdict is not None:
                push({"type": "verdict", "verdict": verdict.model_dump()})
            if fixer_result is not None:
                push({
                    "type": "fix",
                    "original_code": code,
                    "fixed_code": fixer_result.fixed_code,
                    "changes_made": fixer_result.changes_made,
                    "changelog": [c.model_dump() for c in fixer_result.changelog],
                })
            push({"type": "complete", "review_id": review_id})
        except Exception as exc:  # noqa: BLE001
            err = f"{type(exc).__name__}: {exc}"
            with SessionLocal() as db:
                mark_complete(db, review_id, error=err)
            push({"type": "error", "message": err})
        finally:
            push(_DONE)

    yield _sse({"type": "start", "review_id": review_id, "rounds": rounds, "mode": mode.value})
    loop.run_in_executor(None, run_in_thread)

    # Drain the queue until the worker signals DONE. If the client disconnects,
    # this generator is cancelled — the worker keeps running and finishes
    # persistence on its own.
    while True:
        event = await queue.get()
        if event is _DONE:
            break
        yield _sse(event)  # type: ignore[arg-type]

from typing import Protocol

from agents import advocate, critic
from core.models import AgentName, DebateMessage, DebateState
from core.modes import MAX_ROUNDS, ReviewMode


class DebateListener(Protocol):
    """Pluggable rendering surface for the orchestrator.

    The CLI prints to terminal. The future web backend will push these events
    through SSE. Both implement this interface.
    """

    def on_turn_start(self, agent: AgentName, round_number: int, is_initial_review: bool) -> None: ...
    def on_chunk(self, chunk: str) -> None: ...
    def on_turn_complete(self, message: DebateMessage) -> None: ...


class _NullListener:
    def on_turn_start(self, *args, **kwargs) -> None: ...
    def on_chunk(self, *args, **kwargs) -> None: ...
    def on_turn_complete(self, *args, **kwargs) -> None: ...


def _stream_turn(
    state: DebateState,
    agent: AgentName,
    round_number: int,
    listener: DebateListener,
) -> DebateMessage:
    """Run one streamed prose turn (Critic or Advocate, round >= 1 for Adv, >= 2 for Critic)."""
    listener.on_turn_start(agent=agent, round_number=round_number, is_initial_review=False)
    stream = (
        critic.rebut_stream(state, round_number)
        if agent == "CRITIC"
        else advocate.rebut_stream(state, round_number)
    )
    chunks: list[str] = []
    for chunk in stream:
        chunks.append(chunk)
        listener.on_chunk(chunk)
    msg = DebateMessage(agent=agent, round_number=round_number, content="".join(chunks))
    state.transcript.append(msg)
    listener.on_turn_complete(msg)
    return msg


def run_debate(
    code: str,
    language: str | None = None,
    mode: ReviewMode = ReviewMode.STANDARD,
    max_rounds: int | None = None,
    listener: DebateListener | None = None,
) -> DebateState:
    """Run a full debate: Critic's initial review, then N rounds of (Critic, Advocate) exchanges.

    `max_rounds` defaults to the mode's preferred round count. Round 1 is the
    initial structured review followed by the Advocate's first rebuttal. Rounds
    2..N are prose exchanges between Critic and Advocate.
    """
    listener = listener or _NullListener()
    rounds = max_rounds if max_rounds is not None else MAX_ROUNDS[mode]
    state = DebateState(code=code, language=language, max_rounds=rounds, mode=mode)

    # Round 1, Critic: structured initial review (not streamed — JSON mode)
    listener.on_turn_start(agent="CRITIC", round_number=1, is_initial_review=True)
    review = critic.review(code=code, language=language, mode=mode)
    initial_msg = DebateMessage(
        agent="CRITIC",
        round_number=1,
        content=review.model_dump_json(),
        is_initial_review=True,
    )
    state.transcript.append(initial_msg)
    listener.on_turn_complete(initial_msg)

    # Round 1, Advocate: first rebuttal (streamed prose)
    _stream_turn(state, agent="ADVOCATE", round_number=1, listener=listener)

    # Rounds 2..N: Critic then Advocate each round (both prose)
    for round_number in range(2, rounds + 1):
        _stream_turn(state, agent="CRITIC", round_number=round_number, listener=listener)
        _stream_turn(state, agent="ADVOCATE", round_number=round_number, listener=listener)

    return state

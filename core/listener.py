from typing import Protocol

from core.models import AgentName, DebateMessage


class DebateListener(Protocol):
    """Pluggable rendering surface for the debate orchestrator.

    The CLI prints to terminal; the future web backend will push events through
    SSE. Both implement this interface without inheriting from it.
    """

    def on_turn_start(self, agent: AgentName, round_number: int, is_initial_review: bool) -> None: ...
    def on_chunk(self, chunk: str) -> None: ...
    def on_turn_complete(self, message: DebateMessage) -> None: ...


class _NullListener:
    def on_turn_start(self, *args, **kwargs) -> None: ...
    def on_chunk(self, *args, **kwargs) -> None: ...
    def on_turn_complete(self, *args, **kwargs) -> None: ...

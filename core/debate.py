from core.graph import build_pipeline_graph
from core.listener import DebateListener, _NullListener
from core.models import DebateState
from core.modes import MAX_ROUNDS, ReviewMode


def run_debate(
    code: str,
    language: str | None = None,
    mode: ReviewMode = ReviewMode.STANDARD,
    max_rounds: int | None = None,
    listener: DebateListener | None = None,
) -> DebateState:
    """Run the debate loop via LangGraph and return the accumulated DebateState.

    Runs only the debate portion (critic_initial + advocate/critic rounds).
    Judge and Fixer are left to the caller so the interactive approval UI in
    main.py is preserved unchanged.
    """
    listener = listener or _NullListener()  # type: ignore[assignment]
    rounds = max_rounds if max_rounds is not None else MAX_ROUNDS[mode]

    graph = build_pipeline_graph(listener)
    initial = {
        "code": code,
        "language": language,
        "mode": mode.value,
        "max_rounds": rounds,
        "current_round": 0,
        "transcript": [],
        "verdict": None,
        "fixer_result": None,
        "run_verdict": False,   # judge invoked separately by caller
        "run_fixer": False,
    }
    final = graph.invoke(initial)

    return DebateState(
        code=final["code"],
        language=final.get("language"),
        transcript=list(final["transcript"]),
        max_rounds=rounds,
        mode=mode,
    )

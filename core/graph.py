"""LangGraph pipeline for Pair Programmer.

Graph shape:
    START
      └─► critic_initial
            └─► advocate_turn ──┬─► critic_turn ──► advocate_turn (loop)
                                ├─► judge_node ──┬─► fixer_node ──► END
                                │               └─► END
                                └─► END

Round routing (after each advocate_turn):
  current_round < max_rounds  →  critic_turn   (continue debate)
  current_round == max_rounds, run_verdict      →  judge_node
  current_round == max_rounds, not run_verdict  →  END

Fixer routing (after judge_node):
  run_fixer  →  fixer_node
  else       →  END
"""

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from agents import advocate, critic
from agents import fixer as fixer_agent
from agents import judge as judge_agent
from core.listener import DebateListener, _NullListener
from core.models import DebateMessage, DebateState, FixerResult, Verdict
from core.modes import ReviewMode


class PipelineState(TypedDict):
    code: str
    language: str | None
    mode: str                                         # ReviewMode.value
    persona: str | None                               # persona slug, optional
    max_rounds: int
    current_round: int
    transcript: Annotated[list[DebateMessage], operator.add]   # append-only
    verdict: Verdict | None
    fixer_result: FixerResult | None
    run_verdict: bool
    run_fixer: bool


def _to_debate_state(state: PipelineState) -> DebateState:
    """Construct a DebateState view from the current graph state."""
    return DebateState(
        code=state["code"],
        language=state.get("language"),
        transcript=list(state["transcript"]),
        max_rounds=state["max_rounds"],
        mode=ReviewMode(state["mode"]),
        persona=state.get("persona"),
    )


def build_pipeline_graph(listener: DebateListener | None = None):
    """Compile and return the full LangGraph pipeline.

    The listener receives real-time streaming events (on_turn_start, on_chunk,
    on_turn_complete) from inside each graph node, preserving the same live-
    debate experience as the hand-rolled loop.
    """
    _listener: DebateListener = listener or _NullListener()  # type: ignore[assignment]

    # ── Node functions ────────────────────────────────────────────────────────

    def critic_initial(state: PipelineState) -> dict:
        _listener.on_turn_start("CRITIC", 1, True)
        review = critic.review(
            state["code"],
            state.get("language"),
            ReviewMode(state["mode"]),
            persona=state.get("persona"),
        )
        msg = DebateMessage(
            agent="CRITIC",
            round_number=1,
            content=review.model_dump_json(),
            is_initial_review=True,
        )
        _listener.on_turn_complete(msg)
        return {"transcript": [msg], "current_round": 1}

    def advocate_turn(state: PipelineState) -> dict:
        rn = state["current_round"]
        _listener.on_turn_start("ADVOCATE", rn, False)
        ds = _to_debate_state(state)
        chunks: list[str] = []
        for chunk in advocate.rebut_stream(ds, rn):
            chunks.append(chunk)
            _listener.on_chunk(chunk)
        msg = DebateMessage(agent="ADVOCATE", round_number=rn, content="".join(chunks))
        _listener.on_turn_complete(msg)
        return {"transcript": [msg]}

    def critic_turn(state: PipelineState) -> dict:
        rn = state["current_round"] + 1
        _listener.on_turn_start("CRITIC", rn, False)
        ds = _to_debate_state(state)
        chunks: list[str] = []
        for chunk in critic.rebut_stream(ds, rn):
            chunks.append(chunk)
            _listener.on_chunk(chunk)
        msg = DebateMessage(agent="CRITIC", round_number=rn, content="".join(chunks))
        _listener.on_turn_complete(msg)
        return {"transcript": [msg], "current_round": rn}

    def judge_node(state: PipelineState) -> dict:
        verdict = judge_agent.synthesize(_to_debate_state(state))
        return {"verdict": verdict}

    def fixer_node(state: PipelineState) -> dict:
        if state.get("fixer_result") is not None:
            return {}
        result = fixer_agent.fix(state["code"], state["verdict"], state.get("language"))
        return {"fixer_result": result}

    # ── Conditional routing ───────────────────────────────────────────────────

    def _after_advocate(state: PipelineState) -> str:
        if state["current_round"] < state["max_rounds"]:
            return "critic_turn"
        if state["run_verdict"]:
            return "judge_node"
        return "end"

    def _after_judge(state: PipelineState) -> str:
        return "fixer_node" if state["run_fixer"] else "end"

    # ── Graph assembly ────────────────────────────────────────────────────────

    builder = StateGraph(PipelineState)

    builder.add_node("critic_initial", critic_initial)
    builder.add_node("advocate_turn", advocate_turn)
    builder.add_node("critic_turn", critic_turn)
    builder.add_node("judge_node", judge_node)
    builder.add_node("fixer_node", fixer_node)

    builder.add_edge(START, "critic_initial")
    builder.add_edge("critic_initial", "advocate_turn")
    builder.add_conditional_edges(
        "advocate_turn",
        _after_advocate,
        {"critic_turn": "critic_turn", "judge_node": "judge_node", "end": END},
    )
    builder.add_edge("critic_turn", "advocate_turn")
    builder.add_conditional_edges(
        "judge_node",
        _after_judge,
        {"fixer_node": "fixer_node", "end": END},
    )
    builder.add_edge("fixer_node", END)

    return builder.compile()


def get_mermaid_diagram() -> str:
    """Return the Mermaid diagram of the pipeline (no listener needed)."""
    return build_pipeline_graph().get_graph().draw_mermaid()


def run_pipeline(
    code: str,
    language: str | None = None,
    mode: ReviewMode = ReviewMode.STANDARD,
    max_rounds: int | None = None,
    run_verdict: bool = True,
    run_fixer: bool = False,
    listener: DebateListener | None = None,
    persona: str | None = None,
) -> PipelineState:
    """Run the full pipeline and return the final graph state.

    Use this when you want LangGraph to handle everything end-to-end
    (debate + judge + optional fixer) in one shot.  For the interactive
    per-item fixer approval flow, call run_debate() then invoke the judge
    and fixer separately from main.py.
    """
    from core.modes import MAX_ROUNDS
    rounds = max_rounds if max_rounds is not None else MAX_ROUNDS[mode]

    graph = build_pipeline_graph(listener)
    initial: PipelineState = {
        "code": code,
        "language": language,
        "mode": mode.value,
        "persona": persona,
        "max_rounds": rounds,
        "current_round": 0,
        "transcript": [],
        "verdict": None,
        "fixer_result": None,
        "run_verdict": run_verdict,
        "run_fixer": run_fixer,
    }
    return graph.invoke(initial)

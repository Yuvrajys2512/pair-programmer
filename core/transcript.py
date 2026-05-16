from core.models import AgentName, CriticReview, DebateState
from core.text import number_lines


def _render_initial_review(content: str) -> str:
    """Render the structured initial review as readable markdown for the next agent to consume."""
    review = CriticReview.model_validate_json(content)
    lines = [f"**Summary:** {review.summary}", ""]
    if not review.items:
        lines.append("(No issues raised.)")
        return "\n".join(lines)
    for item in review.items:
        loc = f" line {item.line_number}" if item.line_number is not None else ""
        lines.append(
            f"- **[{item.severity}] [{item.category}]{loc}** — {item.issue}  \n"
            f"  *Fix:* {item.suggestion}"
        )
    return "\n".join(lines)


def _format_transcript(state: DebateState) -> str:
    if not state.transcript:
        return "(No messages yet — you are speaking first.)"
    blocks: list[str] = []
    for msg in state.transcript:
        body = _render_initial_review(msg.content) if msg.is_initial_review else msg.content
        blocks.append(f"### Round {msg.round_number} — {msg.agent}\n\n{body}")
    return "\n\n".join(blocks)


_OPENING_GUARD = (
    "Do NOT open your response with meta-praise of your opponent "
    "('The Critic's persistence is commendable', 'The Advocate raises valid points', etc.). "
    "Open with your actual position in one direct sentence."
)


def _turn_instruction(role: AgentName, round_number: int, max_rounds: int) -> str:
    if role == "ADVOCATE":
        if round_number == 1:
            body = (
                "Respond to the Critic's initial review. Defend the parts the Critic "
                "over-attacked, concede the unwinnable bugs, push back on inflated severity "
                "or weak evidence, and surface any strengths the Critic missed. "
                "Plain prose, 150-350 words."
            )
        else:
            body = (
                "Respond to the Critic's latest message. Do not repeat points you have "
                "already made. Introduce at least one NEW argument, observation, or sharpened "
                "formulation. If the Critic's last point was strong, concede cleanly. "
                "Plain prose, 150-350 words."
            )
    else:  # CRITIC in a debate turn (round >= 2)
        body = (
            "The Advocate has responded. Push back where you were right and they were wrong, "
            "concede cleanly where they made a fair point, and either find at least one NEW "
            "issue or deepen one of your existing points with new evidence. Do not repeat "
            "yourself. Plain prose, 150-350 words."
        )
    return f"{body}\n\n{_OPENING_GUARD}"


def build_debate_user_prompt(state: DebateState, role: AgentName, round_number: int) -> str:
    """Assemble the user prompt for a debate turn: code + transcript + this-turn instruction."""
    lang = state.language or ""
    parts: list[str] = [
        f"You are now in Round {round_number} of {state.max_rounds}.",
        f"You are speaking as THE {role}.",
        "",
        "## The code under review",
        "",
        f"```{lang}",
        number_lines(state.code),
        "```",
        "",
        "## The debate so far",
        "",
        _format_transcript(state),
        "",
        "## Your task this turn",
        "",
        _turn_instruction(role, round_number, state.max_rounds),
        "",
        "Speak in character. Plain prose only — no JSON, no meta-commentary about being an AI "
        "or about the debate format itself. Address points directly and cite line numbers when applicable.",
    ]
    return "\n".join(parts)

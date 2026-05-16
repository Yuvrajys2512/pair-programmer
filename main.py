import argparse
import sys
from pathlib import Path

# Force UTF-8 on Windows consoles so debate separators and Rich glyphs render correctly.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from agents.critic import review as critic_review
from agents.judge import synthesize as judge_synthesize
from core.debate import run_debate
from core.models import ActionItem, AgentName, CriticReview, DebateMessage, ReviewItem, Verdict

console = Console()


SEVERITY_COLORS = {
    "CRITICAL": "bold red",
    "HIGH": "red",
    "MEDIUM": "yellow",
    "LOW": "cyan",
}

CATEGORY_ICONS = {
    "BUG": "[BUG]",
    "SECURITY": "[SEC]",
    "EDGE_CASE": "[EDGE]",
    "PERF": "[PERF]",
    "DESIGN": "[DESIGN]",
    "STYLE": "[STYLE]",
}

AGENT_COLOR = {
    "CRITIC": "red",
    "ADVOCATE": "blue",
}


def detect_language(path: Path) -> str | None:
    return {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".jsx": "jsx",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".rb": "ruby",
    }.get(path.suffix.lower())


# --- Renderers shared between solo and debate modes ------------------------


def render_item(item: ReviewItem) -> Panel:
    severity_color = SEVERITY_COLORS.get(item.severity, "white")
    icon = CATEGORY_ICONS.get(item.category, f"[{item.category}]")
    header = Text()
    header.append(f"{icon} ", style="bold")
    header.append(item.severity, style=severity_color)
    header.append("  " + item.category, style="dim")
    if item.line_number is not None:
        header.append(f"  line {item.line_number}", style="dim")
    body = Text()
    body.append("Issue: ", style="bold")
    body.append(item.issue + "\n")
    body.append("Fix:   ", style="bold")
    body.append(item.suggestion)
    return Panel(body, title=header, title_align="left", border_style=severity_color)


def render_review_panel(review: CriticReview) -> None:
    console.print()
    console.print(Panel(review.summary, title="Critic's opening verdict", border_style="magenta"))
    console.print()
    if not review.items:
        console.print("[green]No issues raised.[/green]")
        return
    counts = Table(show_header=True, header_style="bold")
    counts.add_column("Severity")
    counts.add_column("Count", justify="right")
    by_severity: dict[str, int] = {}
    for it in review.items:
        by_severity[it.severity] = by_severity.get(it.severity, 0) + 1
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        if sev in by_severity:
            counts.add_row(Text(sev, style=SEVERITY_COLORS[sev]), str(by_severity[sev]))
    console.print(counts)
    console.print()
    for item in review.items:
        console.print(render_item(item))


def render_solo_review(review: CriticReview, code_path: Path) -> None:
    console.print()
    console.rule(f"[bold]The Critic reviewed[/bold] {code_path.name}")
    render_review_panel(review)


# --- Verdict renderer ------------------------------------------------------


def _score_color(score: int) -> str:
    if score >= 9:
        return "bold green"
    if score >= 7:
        return "green"
    if score >= 5:
        return "yellow"
    if score >= 3:
        return "red"
    return "bold red"


def render_verdict(verdict: Verdict) -> None:
    console.print()
    console.rule("[bold magenta]The Judge's Verdict[/bold magenta]")
    console.print()

    # Header: score + winner + summary
    header = Text()
    header.append("Score: ", style="bold")
    header.append(f"{verdict.score}/10", style=_score_color(verdict.score))
    header.append("   |   ", style="dim")
    header.append("Winner: ", style="bold")
    header.append(verdict.winner, style=f"bold {AGENT_COLOR[verdict.winner]}")
    console.print(Panel(verdict.summary, title=header, title_align="left", border_style="magenta"))
    console.print()

    # Why the winner won
    console.print(Panel(
        verdict.winner_reasoning,
        title=Text(f"Why the {verdict.winner} won", style=f"bold {AGENT_COLOR[verdict.winner]}"),
        title_align="left",
        border_style=AGENT_COLOR[verdict.winner],
    ))
    console.print()

    # Two-column-ish layout for wins (rendered sequentially for terminal readability)
    if verdict.critic_wins:
        body = "\n".join(f"- {w}" for w in verdict.critic_wins)
        console.print(Panel(body, title="The Critic was right about", title_align="left", border_style="red"))
    if verdict.advocate_wins:
        body = "\n".join(f"- {w}" for w in verdict.advocate_wins)
        console.print(Panel(body, title="The Advocate was right about", title_align="left", border_style="blue"))

    # Strengths (the silver lining)
    if verdict.strengths:
        body = "\n".join(f"- {s}" for s in verdict.strengths)
        console.print(Panel(body, title="Strengths to preserve", title_align="left", border_style="green"))

    # Action items
    if verdict.action_items:
        table = Table(title="Action items", show_header=True, header_style="bold", title_style="bold")
        table.add_column("#", justify="right", style="dim")
        table.add_column("Priority")
        table.add_column("Lines", style="dim")
        table.add_column("Action")
        for i, item in enumerate(verdict.action_items, 1):
            lines = ", ".join(str(n) for n in item.affected_lines) if item.affected_lines else "-"
            table.add_row(
                str(i),
                Text(item.priority, style=SEVERITY_COLORS.get(item.priority, "white")),
                lines,
                item.description,
            )
        console.print(table)


# --- Debate-mode listener -------------------------------------------------


class TerminalDebateListener:
    """Streams the debate to the terminal as it unfolds."""

    def on_turn_start(self, agent: AgentName, round_number: int, is_initial_review: bool) -> None:
        color = AGENT_COLOR[agent]
        suffix = " (initial review)" if is_initial_review else ""
        title = Text()
        title.append(f"Round {round_number} ", style="bold")
        title.append(f": {agent}", style=f"bold {color}")
        title.append(suffix, style="dim")
        console.print()
        console.print(Rule(title=title, style=color))
        console.print()

    def on_chunk(self, chunk: str) -> None:
        # Print raw — Rich would re-interpret markup, which we don't want for streamed prose
        sys.stdout.write(chunk)
        sys.stdout.flush()

    def on_turn_complete(self, message: DebateMessage) -> None:
        if message.is_initial_review:
            review = CriticReview.model_validate_json(message.content)
            render_review_panel(review)
            return
        # Newline at end of streamed prose
        sys.stdout.write("\n")
        sys.stdout.flush()


# --- CLI entry -------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pair Programmer — two agents debate your code."
    )
    parser.add_argument("file", type=Path, help="Path to the code file to review.")
    parser.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="Number of debate rounds (default: 3). Round 1 is the initial review + Advocate's first reply.",
    )
    parser.add_argument(
        "--solo",
        action="store_true",
        help="Skip the debate. Only the Critic produces a one-shot structured review (Phase 1 mode).",
    )
    parser.add_argument(
        "--verdict",
        action="store_true",
        help="After the debate, ask the Judge to synthesize a structured verdict.",
    )
    parser.add_argument(
        "--show-code",
        action="store_true",
        help="Print the source file before reviewing.",
    )
    args = parser.parse_args()

    path: Path = args.file
    if not path.exists():
        console.print(f"[red]File not found:[/red] {path}")
        return 1

    code = path.read_text(encoding="utf-8")
    language = detect_language(path)

    if args.show_code:
        console.print(Panel(Syntax(code, language or "text", line_numbers=True), title=str(path)))

    if args.solo:
        with console.status("[bold]The Critic is reading your code...[/bold]", spinner="dots"):
            try:
                result = critic_review(code=code, language=language)
            except Exception as exc:
                console.print(f"[red]Review failed:[/red] {exc}")
                return 2
        render_solo_review(result, path)
        return 0

    # Debate mode
    if args.rounds < 1:
        console.print("[red]--rounds must be at least 1.[/red]")
        return 1

    console.print()
    console.rule(f"[bold magenta]Debate begins:[/bold magenta] {path.name}  ([dim]{args.rounds} rounds[/dim])")

    try:
        state = run_debate(
            code=code,
            language=language,
            max_rounds=args.rounds,
            listener=TerminalDebateListener(),
        )
    except Exception as exc:
        console.print(f"\n[red]Debate failed:[/red] {exc}")
        return 2

    console.print()
    console.rule("[bold magenta]Debate complete[/bold magenta]")
    console.print(
        f"[dim]{len(state.transcript)} messages across {state.max_rounds} rounds.[/dim]"
    )

    if args.verdict:
        console.print()
        with console.status("[bold]The Judge is synthesizing the verdict...[/bold]", spinner="dots"):
            try:
                verdict = judge_synthesize(state)
            except Exception as exc:
                console.print(f"[red]Verdict synthesis failed:[/red] {exc}")
                return 2
        render_verdict(verdict)

    return 0


if __name__ == "__main__":
    sys.exit(main())

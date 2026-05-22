import argparse
import difflib
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
from agents.fixer import fix as fixer_fix
from agents.judge import synthesize as judge_synthesize
from core.debate import run_debate
from core.graph import get_mermaid_diagram, run_pipeline
from core.models import ActionItem, AgentName, ChangeEntry, CriticReview, DebateMessage, FixerResult, ReviewItem, Verdict
from core.modes import MAX_ROUNDS, ReviewMode
from core.personas import list_personas, validate_persona

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


# --- Fixer renderers and orchestration ------------------------------------


def render_diff(original: str, fixed: str, fromfile: str, tofile: str) -> None:
    diff_lines = list(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            fixed.splitlines(keepends=True),
            fromfile=fromfile,
            tofile=tofile,
            lineterm="",
        )
    )
    if not diff_lines:
        console.print("[dim]No textual differences found.[/dim]")
        return
    diff_text = "\n".join(line.rstrip("\n") for line in diff_lines)
    console.print(Syntax(diff_text, "diff", theme="monokai", line_numbers=False))


def render_fixer_changelog(changelog: list[ChangeEntry], action_items: list[ActionItem]) -> None:
    table = Table(title="Changelog", show_header=True, header_style="bold", title_style="bold green")
    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("Action Item", style="dim")
    table.add_column("Change Applied")
    for entry in changelog:
        idx = entry.action_item_index
        ai = action_items[idx - 1] if 1 <= idx <= len(action_items) else None
        ai_label = (ai.description[:48] + "…") if ai and len(ai.description) > 48 else (ai.description if ai else "?")
        table.add_row(str(idx), ai_label, entry.description)
    console.print(table)


def run_fixer(code: str, verdict: Verdict, language: str | None, path: Path) -> None:
    if not verdict.action_items:
        console.print("[dim]No action items — nothing for the Fixer to do.[/dim]")
        return

    console.print()
    console.rule("[bold green]The Fixer[/bold green]")
    console.print()

    with console.status("[bold]The Fixer is rewriting the code...[/bold]", spinner="dots"):
        try:
            result = fixer_fix(code, verdict, language)
        except Exception as exc:
            console.print(f"[red]Fixer failed:[/red] {exc}")
            return

    if not result.changes_made or not result.changelog:
        console.print("[dim]The Fixer found no changes to apply.[/dim]")
        return

    # Show the diff
    console.print("[bold]Proposed changes:[/bold]")
    console.print()
    render_diff(
        code,
        result.fixed_code,
        fromfile=str(path),
        tofile=f"{path.stem}_fixed{path.suffix}",
    )
    console.print()
    render_fixer_changelog(result.changelog, verdict.action_items)
    console.print()

    # Per-item confirmation
    approved_indices: set[int] = set()
    console.print("[bold]Review each fix — press Enter or Y to apply, N to skip:[/bold]")
    console.print()
    for entry in result.changelog:
        short = entry.description[:72] + ("…" if len(entry.description) > 72 else "")
        prompt = f"  Fix [dim]#{entry.action_item_index}[/dim] — {short}  [bold]\\[Y/n]:[/bold] "
        response = console.input(prompt).strip().lower()
        if response in ("", "y", "yes"):
            approved_indices.add(entry.action_item_index)

    if not approved_indices:
        console.print()
        console.print("[dim]No fixes approved. Nothing written.[/dim]")
        return

    if len(approved_indices) == len(result.changelog):
        final_code = result.fixed_code
    else:
        # Re-run with only the approved action items
        seen: set[int] = set()
        approved_items: list[ActionItem] = []
        for entry in result.changelog:
            idx = entry.action_item_index
            if idx in approved_indices and idx not in seen and 1 <= idx <= len(verdict.action_items):
                seen.add(idx)
                approved_items.append(verdict.action_items[idx - 1])

        filtered_verdict = verdict.model_copy(update={"action_items": approved_items})
        console.print()
        with console.status("[bold]Re-running with approved fixes only...[/bold]", spinner="dots"):
            try:
                result2 = fixer_fix(code, filtered_verdict, language)
            except Exception as exc:
                console.print(f"[red]Re-run failed:[/red] {exc}")
                return
        final_code = result2.fixed_code

    out_path = path.parent / f"{path.stem}_fixed{path.suffix}"
    out_path.write_text(final_code, encoding="utf-8")
    console.print()
    console.print(
        Panel(
            f"[bold green]Fixed code written to:[/bold green] {out_path}\n"
            f"[dim]{len(approved_indices)} fix(es) applied.[/dim]",
            border_style="green",
        )
    )


# --- Full-graph (LangGraph end-to-end) ------------------------------------


def _run_full_graph(
    code: str,
    language: str | None,
    mode: ReviewMode,
    args,
    path: Path,
    persona: str | None = None,
) -> int:
    """Run the entire pipeline through LangGraph in one shot.

    Debate + Judge + Fixer all execute as graph nodes. The interactive
    per-item fixer approval is skipped — all action items are applied
    automatically. This demonstrates the full LangGraph state graph.
    """
    rounds = args.rounds if args.rounds is not None else MAX_ROUNDS[mode]
    if rounds < 1:
        console.print("[red]--rounds must be at least 1.[/red]")
        return 1

    run_verdict = True
    run_fixer = args.fix or args.full_graph

    persona_suffix = f", persona: {persona}" if persona else ""
    console.print()
    console.rule(
        f"[bold magenta]LangGraph pipeline:[/bold magenta] {path.name}  "
        f"([dim]{mode.value} mode, {rounds} rounds{persona_suffix}[/dim])"
    )

    listener = TerminalDebateListener()
    try:
        final = run_pipeline(
            code=code,
            language=language,
            mode=mode,
            max_rounds=rounds,
            run_verdict=run_verdict,
            run_fixer=run_fixer,
            listener=listener,
            persona=persona,
        )
    except Exception as exc:
        console.print(f"\n[red]Pipeline failed:[/red] {exc}")
        return 2

    console.print()
    console.rule("[bold magenta]Debate complete[/bold magenta]")
    console.print(f"[dim]{len(final['transcript'])} messages across {rounds} rounds.[/dim]")

    if final.get("verdict"):
        render_verdict(final["verdict"])

    if final.get("fixer_result"):
        result: FixerResult = final["fixer_result"]
        if not result.changes_made or not result.changelog:
            console.print()
            console.print("[dim]The Fixer found no changes to apply.[/dim]")
        else:
            console.print()
            console.rule("[bold green]The Fixer[/bold green]")
            console.print()
            console.print("[bold]Applied changes:[/bold]")
            console.print()
            render_diff(code, result.fixed_code, fromfile=str(path), tofile=f"{path.stem}_fixed{path.suffix}")
            console.print()
            render_fixer_changelog(result.changelog, final["verdict"].action_items)
            out_path = path.parent / f"{path.stem}_fixed{path.suffix}"
            out_path.write_text(result.fixed_code, encoding="utf-8")
            console.print()
            console.print(
                Panel(
                    f"[bold green]Fixed code written to:[/bold green] {out_path}\n"
                    f"[dim]{len(result.changelog)} fix(es) applied (all approved automatically).[/dim]",
                    border_style="green",
                )
            )

    return 0


# --- CLI entry -------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pair Programmer — two agents debate your code."
    )
    parser.add_argument(
        "file",
        type=Path,
        nargs="?",
        help="Path to the code file to review. Not required when --graph-diagram is used.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=[m.value for m in ReviewMode],
        default=ReviewMode.STANDARD.value,
        help="Review intensity: roast (2 rounds, brutal+funny), standard (3, default), deep (5, architectural).",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=None,
        help="Override the number of debate rounds. Defaults to the mode's preferred count.",
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
        "--fix",
        action="store_true",
        help="After the verdict, rewrite the code to address the action items. Implies --verdict.",
    )
    parser.add_argument(
        "--show-code",
        action="store_true",
        help="Print the source file before reviewing.",
    )
    parser.add_argument(
        "--graph-diagram",
        action="store_true",
        help="Print the LangGraph Mermaid diagram of the pipeline and exit.",
    )
    parser.add_argument(
        "--full-graph",
        action="store_true",
        help=(
            "Run the complete pipeline (debate + judge + fixer) through LangGraph "
            "in one shot. Implies --verdict and --fix. Skips the interactive per-item "
            "fixer approval — all action items are applied automatically."
        ),
    )
    parser.add_argument(
        "--persona",
        type=str,
        default=None,
        help="Persona overlay slug (e.g., 'mentor', 'security_auditor'). See --list-personas.",
    )
    parser.add_argument(
        "--list-personas",
        action="store_true",
        help="List available personas and exit.",
    )
    args = parser.parse_args()

    if args.list_personas:
        console.print()
        console.rule("[bold magenta]Available personas[/bold magenta]")
        console.print()
        personas = list_personas()
        if not personas:
            console.print("[dim]No personas registered. Add files under agents/prompts/personas/.[/dim]")
            return 0
        table = Table(show_header=True, header_style="bold")
        table.add_column("Slug", style="bold cyan")
        table.add_column("Name")
        table.add_column("Description")
        for p in personas:
            short = p.description if len(p.description) <= 80 else p.description[:77] + "…"
            table.add_row(p.slug, p.name, short)
        console.print(table)
        console.print()
        console.print("[dim]Use --persona <slug> to apply one.[/dim]")
        return 0

    try:
        persona = validate_persona(args.persona)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    if args.graph_diagram:
        console.print()
        console.rule("[bold magenta]LangGraph Pipeline — Mermaid Diagram[/bold magenta]")
        console.print()
        console.print(get_mermaid_diagram())
        return 0

    if args.file is None:
        console.print("[red]A code file is required.[/red]  Usage: main.py <file> [options]")
        return 1

    path: Path = args.file
    if not path.exists():
        console.print(f"[red]File not found:[/red] {path}")
        return 1

    code = path.read_text(encoding="utf-8")
    language = detect_language(path)

    if args.show_code:
        console.print(Panel(Syntax(code, language or "text", line_numbers=True), title=str(path)))

    mode = ReviewMode(args.mode)

    if args.full_graph:
        return _run_full_graph(code, language, mode, args, path, persona)

    if args.solo:
        with console.status("[bold]The Critic is reading your code...[/bold]", spinner="dots"):
            try:
                result = critic_review(code=code, language=language, mode=mode, persona=persona)
            except Exception as exc:
                console.print(f"[red]Review failed:[/red] {exc}")
                return 2
        render_solo_review(result, path)
        return 0

    # Debate mode
    rounds = args.rounds if args.rounds is not None else MAX_ROUNDS[mode]
    if rounds < 1:
        console.print("[red]--rounds must be at least 1.[/red]")
        return 1

    persona_suffix = f", persona: {persona}" if persona else ""
    console.print()
    console.rule(
        f"[bold magenta]Debate begins:[/bold magenta] {path.name}  "
        f"([dim]{mode.value} mode, {rounds} rounds{persona_suffix}[/dim])"
    )

    try:
        state = run_debate(
            code=code,
            language=language,
            mode=mode,
            max_rounds=rounds,
            listener=TerminalDebateListener(),
            persona=persona,
        )
    except Exception as exc:
        console.print(f"\n[red]Debate failed:[/red] {exc}")
        return 2

    console.print()
    console.rule("[bold magenta]Debate complete[/bold magenta]")
    console.print(
        f"[dim]{len(state.transcript)} messages across {state.max_rounds} rounds.[/dim]"
    )

    if args.verdict or args.fix:
        console.print()
        with console.status("[bold]The Judge is synthesizing the verdict...[/bold]", spinner="dots"):
            try:
                verdict = judge_synthesize(state)
            except Exception as exc:
                console.print(f"[red]Verdict synthesis failed:[/red] {exc}")
                return 2
        render_verdict(verdict)

        if args.fix:
            run_fixer(code, verdict, language, path)

    return 0


if __name__ == "__main__":
    sys.exit(main())

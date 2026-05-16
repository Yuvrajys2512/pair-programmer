import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from agents.critic import review
from core.models import CriticReview, ReviewItem

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


def render_review(review_result: CriticReview, code_path: Path) -> None:
    console.print()
    console.rule(f"[bold]The Critic reviewed[/bold] {code_path.name}")
    console.print()
    console.print(Panel(review_result.summary, title="Verdict", border_style="magenta"))
    console.print()

    if not review_result.items:
        console.print("[green]No issues raised.[/green]")
        return

    counts = Table(show_header=True, header_style="bold")
    counts.add_column("Severity")
    counts.add_column("Count", justify="right")
    by_severity: dict[str, int] = {}
    for it in review_result.items:
        by_severity[it.severity] = by_severity.get(it.severity, 0) + 1
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        if sev in by_severity:
            counts.add_row(Text(sev, style=SEVERITY_COLORS[sev]), str(by_severity[sev]))
    console.print(counts)
    console.print()

    for item in review_result.items:
        console.print(render_item(item))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pair Programmer — Phase 1: have the Critic review a code file."
    )
    parser.add_argument("file", type=Path, help="Path to the code file to review.")
    parser.add_argument(
        "--show-code",
        action="store_true",
        help="Print the source file before the review.",
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

    with console.status("[bold]The Critic is reading your code...[/bold]", spinner="dots"):
        try:
            result = review(code=code, language=language)
        except Exception as exc:
            console.print(f"[red]Review failed:[/red] {exc}")
            return 2

    render_review(result, path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

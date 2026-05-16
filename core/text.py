def number_lines(code: str) -> str:
    """Prefix each line with its 1-indexed line number for accurate citation by the model."""
    lines = code.splitlines()
    width = len(str(len(lines))) if lines else 1
    return "\n".join(f"{str(i + 1).rjust(width)} | {line}" for i, line in enumerate(lines))

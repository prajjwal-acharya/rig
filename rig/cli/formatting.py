from __future__ import annotations

from collections.abc import Sequence


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    size_kb = size_bytes / 1024
    if size_kb < 1024:
        return f"{trim(size_kb)} KB"
    return f"{trim(size_kb / 1024)} MB"


def trim(value: float) -> str:
    text = f"{value:.1f}"
    return text.removesuffix(".0")


def format_count(value: int) -> str:
    return f"{value:,}"


def format_duration(seconds: float) -> str:
    if seconds >= 1:
        return f"{seconds:.1f} s"
    return f"{seconds * 1000:.0f} ms"


def section(title: str) -> None:
    print(title)
    print("─" * len(title))


def progress(message: str) -> None:
    print(f"{message}...")


def done() -> None:
    print("Done.")


def print_count_table(rows: Sequence[tuple[str, int]], *, indent: str = "") -> None:
    if not rows:
        print(f"{indent}(None)")
        return
    label_width = max(len(label) for label, _ in rows)
    for label, value in rows:
        print(f"{indent}{label:<{label_width}}  {format_count(value):>12}")


def print_percentage_table(rows: Sequence[tuple[str, float]], *, indent: str = "") -> None:
    if not rows:
        print(f"{indent}(None)")
        return
    label_width = max(len(label) for label, _ in rows)
    for label, percentage in rows:
        print(f"{indent}{label:<{label_width}}  {percentage:>6.1f}%")

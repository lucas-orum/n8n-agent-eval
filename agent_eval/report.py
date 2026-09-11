"""Console and Markdown reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .models import RunSummary

GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
OFF = "\033[0m"


def print_console(summary: RunSummary, color: bool = True) -> None:
    def paint(text: str, code: str) -> str:
        return f"{code}{text}{OFF}" if color else text

    print()
    print(paint(f"  Grade  {summary.grade} / 10", BOLD))
    print(
        f"  {summary.passed_criteria} of {summary.total_criteria} criteria passed"
        f"  ({_pct(summary.passed_criteria, summary.total_criteria)})"
    )
    print(
        f"  {len(summary.clean_cases)} of {len(summary.cases)} cases ran with no divergence at all"
    )
    print()

    width = max((len(c.case.id) for c in summary.cases), default=4)
    for case in summary.cases:
        mark = paint("PASS", GREEN) if case.passed else paint("FAIL", RED)
        score = "error" if case.error else f"{case.passed_count}/{case.total}"
        print(f"  {mark}  {case.case.id.ljust(width)}  {score.rjust(7)}  {paint(case.case.description, DIM)}")
        if case.error:
            print(f"        {paint(case.error, RED)}")
            continue
        for failure in case.failures:
            label = failure.criterion.description or failure.criterion.kind
            print(f"        {paint('x', RED)} {label}")
            if failure.detail:
                print(f"          {paint(failure.detail, DIM)}")
    print()


def _pct(part: int, whole: int) -> str:
    return f"{round(100 * part / whole)}%" if whole else "0%"


def write_markdown(summary: RunSummary, path: Path, title: Optional[str] = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# {title or 'Agent evaluation'}",
        "",
        f"**{summary.grade} / 10**",
        "",
        f"{summary.passed_criteria} of {summary.total_criteria} criteria passed "
        f"({_pct(summary.passed_criteria, summary.total_criteria)}).",
        "",
        "| | |",
        "|---|---|",
        f"| Cases with no divergence | {len(summary.clean_cases)} of {len(summary.cases)} |",
        f"| Cases passed | {len(summary.passed_cases)} |",
        f"| Cases failed | {len(summary.failed_cases)} |",
        "",
        "## Cases",
        "",
        "| Case | What it tests | Score | Result |",
        "|---|---|---|---|",
    ]
    for case in summary.cases:
        score = "error" if case.error else f"{case.passed_count}/{case.total}"
        verdict = "passed" if case.passed else "failed"
        lines.append(f"| `{case.case.id}` | {case.case.description} | {score} | {verdict} |")

    lines += ["", "## Divergences", ""]
    any_failure = False
    for case in summary.cases:
        if case.error:
            any_failure = True
            lines += [f"### {case.case.id}", "", f"Run error: {case.error}", ""]
            continue
        if not case.failures:
            continue
        any_failure = True
        lines += [f"### {case.case.id} ({case.passed_count}/{case.total})", ""]
        for failure in case.failures:
            label = failure.criterion.description or failure.criterion.kind
            lines.append(f"- **{label}**")
            if failure.detail:
                lines.append(f"  - {failure.detail}")
        lines.append("")
        for index, reply in enumerate(case.responses):
            lines += [f"<details><summary>Reply #{index}</summary>", "", f"> {reply}", "", "</details>", ""]

    if not any_failure:
        lines.append("None. Every criterion passed.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

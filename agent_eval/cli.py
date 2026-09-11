"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .cases import CaseFileError, load_cases
from .models import RunSummary
from .report import print_console, write_markdown
from .runner import MockRunner, WebhookRunner
from .scoring import score_case


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-eval",
        description="Run scripted conversations against an n8n agent and score the replies "
        "against the rules its specification actually states.",
    )
    parser.add_argument("cases", help="a .yaml case file, or a directory of them")
    parser.add_argument("--url", default=os.getenv("AGENT_WEBHOOK_URL"),
                        help="n8n webhook URL (or set AGENT_WEBHOOK_URL)")
    parser.add_argument("--mock", action="store_true",
                        help="replay mock_replies from the case file instead of calling the agent")
    parser.add_argument("--message-field", default="message")
    parser.add_argument("--session-field", default="sessionId")
    parser.add_argument("--response-path", default="output",
                        help="dotted path to the reply inside the JSON response, e.g. data.0.output")
    parser.add_argument("--header", action="append", default=[], metavar="K:V",
                        help="extra request header, repeatable")
    parser.add_argument("--report", type=Path, help="write a Markdown report to this path")
    parser.add_argument("--title", help="title for the Markdown report")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--fail-under", type=float, default=None, metavar="GRADE",
                        help="exit non-zero when the grade falls below this, for CI")
    return parser


def _headers(raw_headers) -> dict:
    headers = {}
    for item in raw_headers:
        if ":" not in item:
            raise SystemExit(f"bad --header '{item}', expected Key:Value")
        key, value = item.split(":", 1)
        headers[key.strip()] = value.strip()
    return headers


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    try:
        cases = load_cases(args.cases)
    except CaseFileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.mock:
        runner = MockRunner()
    else:
        if not args.url:
            print("error: pass --url or set AGENT_WEBHOOK_URL (or use --mock)", file=sys.stderr)
            return 2
        runner = WebhookRunner(
            url=args.url,
            message_field=args.message_field,
            session_field=args.session_field,
            response_path=args.response_path,
            headers=_headers(args.header),
        )

    summary = RunSummary()
    for case in cases:
        replies, error = runner.run(case)
        summary.cases.append(score_case(case, replies, error))

    print_console(summary, color=not args.no_color)

    if args.report:
        path = write_markdown(summary, args.report, args.title)
        print(f"  report written to {path}\n")

    if args.fail_under is not None and summary.grade < args.fail_under:
        print(f"  grade {summary.grade} is below --fail-under {args.fail_under}\n", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

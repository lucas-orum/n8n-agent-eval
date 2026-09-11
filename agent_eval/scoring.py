"""Scoring rules.

Each criterion kind is a small, deterministic check. The point of keeping them
dumb is that a failing run always names the exact rule that broke, in the same
words the specification uses.
"""

from __future__ import annotations

import re
from typing import Callable, Dict, List

from .models import Case, CaseResult, Criterion, CriterionResult

# Sentence-ending question marks, ignoring ones inside quotes is overkill here.
_QUESTION_MARK = "?"


def _selected(responses: List[str], criterion: Criterion) -> List[str]:
    """The replies this criterion applies to."""
    if criterion.turn is None:
        return responses
    if criterion.turn < len(responses):
        return [responses[criterion.turn]]
    return []


def _where(criterion: Criterion) -> str:
    return "any reply" if criterion.turn is None else f"reply #{criterion.turn}"


def check_contains(responses: List[str], criterion: Criterion) -> CriterionResult:
    needles = criterion.value if isinstance(criterion.value, list) else [criterion.value]
    haystack = " \n ".join(_selected(responses, criterion)).lower()
    missing = [n for n in needles if str(n).lower() not in haystack]
    if missing:
        return CriterionResult(criterion, False, f"missing from {_where(criterion)}: {missing}")
    return CriterionResult(criterion, True)


def check_not_contains(responses: List[str], criterion: Criterion) -> CriterionResult:
    needles = criterion.value if isinstance(criterion.value, list) else [criterion.value]
    found = []
    for reply in _selected(responses, criterion):
        low = reply.lower()
        found += [n for n in needles if str(n).lower() in low]
    if found:
        return CriterionResult(criterion, False, f"forbidden text present: {sorted(set(found))}")
    return CriterionResult(criterion, True)


def check_regex(responses: List[str], criterion: Criterion) -> CriterionResult:
    pattern = re.compile(str(criterion.value), re.IGNORECASE | re.MULTILINE)
    for reply in _selected(responses, criterion):
        if pattern.search(reply):
            return CriterionResult(criterion, True)
    return CriterionResult(criterion, False, f"no match for /{criterion.value}/ in {_where(criterion)}")


def check_max_questions(responses: List[str], criterion: Criterion) -> CriterionResult:
    """Catches the classic failure of stacking two questions into one message."""
    limit = int(criterion.value)
    for index, reply in enumerate(_selected(responses, criterion)):
        count = reply.count(_QUESTION_MARK)
        if count > limit:
            return CriterionResult(
                criterion, False, f"reply #{index} asks {count} questions, limit is {limit}"
            )
    return CriterionResult(criterion, True)


def check_max_replies(responses: List[str], criterion: Criterion) -> CriterionResult:
    limit = int(criterion.value)
    if len(responses) > limit:
        return CriterionResult(criterion, False, f"agent sent {len(responses)} replies, limit is {limit}")
    return CriterionResult(criterion, True)


def check_ends_conversation(responses: List[str], criterion: Criterion) -> CriterionResult:
    """The handoff or closing phrase must be the last thing said, not buried mid-flow."""
    marker = str(criterion.value).lower()
    if not responses:
        return CriterionResult(criterion, False, "agent produced no replies")
    if marker in responses[-1].lower():
        return CriterionResult(criterion, True)
    where = [i for i, r in enumerate(responses) if marker in r.lower()]
    if where:
        return CriterionResult(criterion, False, f"appears at reply #{where[0]} but not at the end")
    return CriterionResult(criterion, False, f"'{criterion.value}' never appears")


CHECKS: Dict[str, Callable[[List[str], Criterion], CriterionResult]] = {
    "contains": check_contains,
    "not_contains": check_not_contains,
    "regex": check_regex,
    "max_questions": check_max_questions,
    "max_replies": check_max_replies,
    "ends_conversation": check_ends_conversation,
}


def score_case(case: Case, responses: List[str], error: str = None) -> CaseResult:
    result = CaseResult(case=case, responses=responses, error=error)
    if error:
        return result
    for criterion in case.criteria:
        check = CHECKS.get(criterion.kind)
        if check is None:
            result.results.append(
                CriterionResult(criterion, False, f"unknown criterion kind '{criterion.kind}'")
            )
            continue
        result.results.append(check(responses, criterion))
    return result

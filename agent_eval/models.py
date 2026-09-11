"""Core data types for the evaluation harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

# Fraction of criteria a case must satisfy to be reported as passing.
PASS_THRESHOLD = 0.7


@dataclass(frozen=True)
class Criterion:
    """A single checkable rule taken from the agent's specification.

    `turn` selects which agent reply the rule applies to (0-based).
    Leave it out to check the whole conversation.
    """

    id: str
    kind: str
    value: Any = None
    description: str = ""
    turn: Optional[int] = None


@dataclass(frozen=True)
class Case:
    """One scripted conversation plus the rules its replies must satisfy."""

    id: str
    description: str
    messages: List[str]
    criteria: List[Criterion]
    # Canned replies so the case can run with --mock, no n8n instance needed.
    mock_replies: Optional[List[str]] = None


@dataclass(frozen=True)
class CriterionResult:
    criterion: Criterion
    passed: bool
    detail: str = ""


@dataclass
class CaseResult:
    case: Case
    responses: List[str] = field(default_factory=list)
    results: List[CriterionResult] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def score(self) -> float:
        if not self.total:
            return 0.0
        return self.passed_count / self.total

    @property
    def passed(self) -> bool:
        return self.error is None and self.score >= PASS_THRESHOLD

    @property
    def failures(self) -> List[CriterionResult]:
        return [r for r in self.results if not r.passed]


@dataclass
class RunSummary:
    cases: List[CaseResult] = field(default_factory=list)

    @property
    def total_criteria(self) -> int:
        return sum(c.total for c in self.cases)

    @property
    def passed_criteria(self) -> int:
        return sum(c.passed_count for c in self.cases)

    @property
    def passed_cases(self) -> List[CaseResult]:
        return [c for c in self.cases if c.passed]

    @property
    def failed_cases(self) -> List[CaseResult]:
        return [c for c in self.cases if not c.passed]

    @property
    def clean_cases(self) -> List[CaseResult]:
        """Cases where every single criterion passed."""
        return [c for c in self.cases if c.total and c.passed_count == c.total]

    @property
    def grade(self) -> float:
        """Overall score on a 0 to 10 scale."""
        if not self.total_criteria:
            return 0.0
        return round(10 * self.passed_criteria / self.total_criteria, 1)

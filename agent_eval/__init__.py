"""Scenario testing for n8n AI agents.

Everybody publishes pretty workflows. Almost nobody publishes how they know the
workflow is still doing what the specification says. This is that missing piece.
"""

__version__ = "0.1.0"

from .models import Case, CaseResult, Criterion, CriterionResult, RunSummary
from .cases import load_cases
from .scoring import score_case
from .runner import MockRunner, WebhookRunner

__all__ = [
    "Case",
    "CaseResult",
    "Criterion",
    "CriterionResult",
    "RunSummary",
    "load_cases",
    "score_case",
    "MockRunner",
    "WebhookRunner",
]

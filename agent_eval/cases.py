"""Load test cases from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import List

import yaml

from .models import Case, Criterion


class CaseFileError(ValueError):
    """Raised when a case file is malformed, with the offending file named."""


def _criterion(raw: dict, case_id: str, index: int) -> Criterion:
    if "kind" not in raw:
        raise CaseFileError(f"case '{case_id}', criterion #{index}: missing 'kind'")
    return Criterion(
        id=raw.get("id") or f"{case_id}-{index}",
        kind=raw["kind"],
        value=raw.get("value"),
        description=raw.get("description", ""),
        turn=raw.get("turn"),
    )


def load_cases(path: Path) -> List[Case]:
    """Read one YAML file, or every .yaml file in a directory."""
    path = Path(path)
    files = sorted(path.glob("*.yaml")) if path.is_dir() else [path]
    if not files:
        raise CaseFileError(f"no .yaml case files found in {path}")

    cases: List[Case] = []
    for file in files:
        data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
        for raw in data.get("cases", []):
            case_id = raw.get("id")
            if not case_id:
                raise CaseFileError(f"{file}: every case needs an 'id'")
            messages = raw.get("messages") or []
            if not messages:
                raise CaseFileError(f"{file}: case '{case_id}' has no messages")
            criteria = [
                _criterion(c, case_id, i) for i, c in enumerate(raw.get("criteria", []))
            ]
            cases.append(
                Case(
                    id=case_id,
                    description=raw.get("description", ""),
                    messages=messages,
                    criteria=criteria,
                    mock_replies=raw.get("mock_replies"),
                )
            )
    return cases

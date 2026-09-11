"""Send a scripted conversation to an agent and collect its replies.

Two runners ship with the tool:

* `WebhookRunner` posts to a live n8n Webhook node, which is how you evaluate a
  real workflow.
* `MockRunner` replays canned replies from the case file, so the suite and the
  example run with no n8n instance at all.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

import requests

from .models import Case


def dig(payload: Any, path: str) -> Any:
    """Walk a dotted path into nested dicts and lists: 'data.0.output'."""
    current = payload
    for part in path.split("."):
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
        else:
            return None
    return current


class WebhookRunner:
    """Posts each user message to an n8n webhook, reusing one session id."""

    def __init__(
        self,
        url: str,
        message_field: str = "message",
        session_field: str = "sessionId",
        response_path: str = "output",
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 90,
    ):
        self.url = url
        self.message_field = message_field
        self.session_field = session_field
        self.response_path = response_path
        self.headers = headers or {}
        self.timeout = timeout

    def run(self, case: Case) -> Tuple[List[str], Optional[str]]:
        session_id = f"eval-{case.id}-{uuid.uuid4().hex[:8]}"
        replies: List[str] = []
        for message in case.messages:
            body = {self.message_field: message, self.session_field: session_id}
            try:
                response = requests.post(
                    self.url, json=body, headers=self.headers, timeout=self.timeout
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                return replies, f"request failed: {exc}"

            try:
                payload = response.json()
            except ValueError:
                replies.append(response.text)
                continue

            reply = dig(payload, self.response_path)
            if reply is None:
                return replies, (
                    f"no value at '{self.response_path}' in the response. "
                    f"Got keys: {list(payload) if isinstance(payload, dict) else type(payload).__name__}"
                )
            replies.append(reply if isinstance(reply, str) else str(reply))
        return replies, None


class MockRunner:
    """Replays `mock_replies` from the case file. Useful for demos and for CI."""

    def run(self, case: Case) -> Tuple[List[str], Optional[str]]:
        replies = getattr(case, "mock_replies", None) or MOCKS.get(case.id)
        if replies is None:
            return [], f"case '{case.id}' has no mock_replies and no registered mock"
        return list(replies), None


MOCKS: Dict[str, List[str]] = {}


def register_mock(case_id: str, replies: List[str]) -> None:
    MOCKS[case_id] = replies

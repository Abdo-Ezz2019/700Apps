"""The only LLM surface the module depends on.

Plug your real client (small model) behind `LLMClient`. Tests use a FakeLLM
(see tests/unit/helpers.py) that reads canned JSON from tests/fixtures/llm/.
"""
from __future__ import annotations

from typing import Any, Dict, Protocol

# task names used by the stages
TASK_TOPIC_LOCATOR = "topic_locator"
TASK_BRIEF = "brief"
TASK_BRIEF_REVIEW = "brief_review"


class LLMClient(Protocol):
    def complete_json(self, task: str, prompt: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Run `prompt` (with structured `payload`) and return the parsed JSON object."""
        ...

"""Error codes and the single exception type used by every stage."""
from __future__ import annotations

from typing import Optional


class ErrorCode:
    # S0
    TOPIC_NOT_FOUND = "TOPIC_NOT_FOUND"
    INPUT_TOO_SHORT = "INPUT_TOO_SHORT"
    LANGUAGE_MISMATCH = "LANGUAGE_MISMATCH"
    INVALID_REQUEST = "INVALID_REQUEST"
    # S1
    BRIEF_INVALID = "BRIEF_INVALID"
    BRIEF_REVIEW_FLAGGED = "BRIEF_REVIEW_FLAGGED"


class PipelineError(Exception):
    """Raised by a stage when the lesson version must be marked `failed`.

    The orchestrator (outside this module) catches it, sets version status to
    `failed` and stores `code` as the failure reason.
    """

    def __init__(self, code: str, message: str = "", stage: Optional[str] = None):
        self.code = code
        self.message = message
        self.stage = stage
        super().__init__(f"[{stage or '?'}] {code}: {message}")

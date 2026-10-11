"""Builds the system prompts with the selected dialect policy appended.

    from prompt_builder import build_prompt
    system = build_prompt("story_sequence_planner", dialect="saudi")

Template ids: "scene_planner", "story_sequence_planner", "scene_compiler".
"""
from __future__ import annotations

import json
from pathlib import Path

try:
    from .dialects import dialect_policy_block
except ImportError:
    from dialects import dialect_policy_block

_TEMPLATES = json.loads(Path(__file__).with_name("prompt_templates.json").read_text(encoding="utf-8"))
TEMPLATE_IDS = [k for k in _TEMPLATES if not k.startswith("_")]


def build_prompt(template_id: str, dialect: str | None = None) -> str:
    if template_id not in TEMPLATE_IDS:
        raise ValueError(f"Unknown template {template_id!r}. Choose one of: {', '.join(TEMPLATE_IDS)}")
    return _TEMPLATES[template_id] + "\n\n" + dialect_policy_block(dialect)

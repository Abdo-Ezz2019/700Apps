"""Narrative persona contract. The persona inhabits the story; it is not a teacher.

Changes from the original project file:
  * build_persona() takes a `dialect` argument ("egyptian" | "saudi" | "msa" | "english").
  * Persona metadata (identity, voice, relationship) is written in English: it is
    instruction data for the LLM, not text shown to the student. The persona's
    *speech* follows the selected dialect (see dialects.py / dialect_profiles.json).
  * The persona carries `dialect` and `language` so every scene stays consistent.
"""
from __future__ import annotations

from typing import Any

try:
    from .dialects import get_dialect
except ImportError:  # running as a standalone folder
    from dialects import get_dialect

DEFAULT_IDENTITY = "an in-world narrator who observes the event from inside the story world"
DEFAULT_VOICE = "curious and warm; tells what it sees and never lectures"
DEFAULT_RELATIONSHIP = "partner in discovery"
DEFAULT_SCENE_ACTION = "follows the event"


def build_persona(
    outline: dict[str, Any],
    previous: dict[str, Any] | None = None,
    dialect: str | None = None,
) -> dict[str, Any]:
    supplied = outline.get("persona") if isinstance(outline.get("persona"), dict) else {}
    prior = previous.get("persona") if isinstance(previous, dict) and isinstance(previous.get("persona"), dict) else {}

    # Dialect precedence: explicit argument > previous scene's persona > project default.
    profile = get_dialect(dialect or prior.get("dialect"))

    # Keep a model-authored identity when available; never invent a fixed mascot/name.
    persona = {
        "role": "in_story_character" if supplied.get("name") or supplied.get("identity") else "in_world_narrative_voice",
        "name": supplied.get("name") or prior.get("name"),
        "identity": supplied.get("identity") or prior.get("identity") or DEFAULT_IDENTITY,
        "voice": supplied.get("voice") or prior.get("voice") or f"{DEFAULT_VOICE}; speaks in {profile['label']}",
        "dialect": profile["id"],
        "language": profile["language_code"],
        "emotional_beat": supplied.get("emotional_beat") or "curiosity",
        "scene_action": supplied.get("scene_action") or outline.get("story_beat", DEFAULT_SCENE_ACTION),
        "behavior": ["observe", "wonder", "react", "invite_discovery"],
        "teaching_role": False,
    }
    supplied_state = supplied.get("story_state") if isinstance(supplied.get("story_state"), dict) else {}
    prior_state = prior.get("story_state") if isinstance(prior.get("story_state"), dict) else {}
    current_discoveries = outline.get("discovery_node_ids", [])
    if not isinstance(current_discoveries, list):
        current_discoveries = []
    if not current_discoveries and outline.get("story_function") in {"discovery", "resolution", "payoff"}:
        current_discoveries = outline.get("node_ids", []) if isinstance(outline.get("node_ids"), list) else []
    discoveries = list(dict.fromkeys(
        [item for item in prior_state.get("discovered_node_ids", []) if isinstance(item, str)]
        + [item for item in current_discoveries if isinstance(item, str)]
    ))
    persona["story_state"] = {
        "current_goal": supplied_state.get("current_goal") or outline.get("character_goal") or outline.get("story_goal") or prior_state.get("current_goal", ""),
        "known_node_ids": discoveries,
        "discovered_node_ids": discoveries,
        "beliefs": supplied_state.get("beliefs", prior_state.get("beliefs", [])),
        "emotional_state": supplied_state.get("emotional_state") or persona["emotional_beat"],
        "relationship_with_student": supplied_state.get("relationship_with_student") or prior_state.get("relationship_with_student", DEFAULT_RELATIONSHIP),
    }
    if not persona["name"]:
        persona.pop("name")
    return persona

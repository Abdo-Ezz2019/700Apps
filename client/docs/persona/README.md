# Darb Persona and Teaching Method Pack

A standalone pack containing **only the persona and its teaching method** from the `INteractive` project. All documents are in English. Narration dialect is configurable: **Egyptian, Saudi, MSA (fusha) or English**.

## Files (suggested reading order)

| File | Contents |
|---|---|
| `TEACHING_METHOD.md` | The method: story first, a scene is an event, interaction and narration rules, QA |
| `PERSONA.md` | The persona: voice, behavior, persistent state, good and bad examples, validator rules |
| `DIALECTS.md` | The four dialect options, what each controls, samples, how to add one |
| `PROMPTS.md` | The original system prompts and narration rules, with the dialect made configurable |
| `dialect_profiles.json` | Single source of truth for dialect settings (edit to tune) |
| `dialects.py` | Loads profiles and builds the LANGUAGE POLICY block |
| `prompt_builder.py` + `prompt_templates.json` | `build_prompt(template_id, dialect)` |
| `persona_engine.py` | `build_persona(outline, previous, dialect)` |
| `persona_examples.json` | Real outputs of `build_persona` |

## Quick start

```python
from persona_engine import build_persona
from prompt_builder import build_prompt

dialect = "saudi"   # "egyptian" | "saudi" | "msa" | "english"

system  = build_prompt("story_sequence_planner", dialect=dialect)   # also: scene_planner, scene_compiler
persona = build_persona({"story_beat": "Two marks in the hallway", "story_function": "setup"}, dialect=dialect)
```

Requires Python 3.9+ and no third-party packages.

## The idea in three lines

- The persona is a narrator or character **inside the story**, never a teacher (`teaching_role = false`).
- A lesson is one connected causal story. Every scene is an event; every interaction is an action with a visible consequence.
- Educational truth comes from the textbook and the KG. The persona only tells what happens. Dialect changes the voice, never the facts or the rules.

## Open decisions

1. Default dialect (currently `msa`; the original project used Egyptian).
2. Voice levels for older learners (middle and secondary school).
3. Whether hints after a wrong answer use the persona's voice or a neutral one.
4. Native review of the Saudi, MSA and English samples (written by an AI model).

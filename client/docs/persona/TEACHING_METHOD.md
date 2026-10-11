# Darb Teaching Method

Standalone document. It explains **how a textbook lesson becomes an interactive, story-driven learning experience**. Renderers, RAG and motion are out of scope.

---

## 1. Core principle

```text
Knowledge Graph  = educational truth
AI               = planner, not a source of facts
Story            = leads the experience
Learning intent  = a constraint on the story, not its director
```

- **Story first; learning objectives constrain it.** We do not build one explanation card per concept. We build an event in the student's story from which the concept is discovered.
- Never add a fact that is not supported by the textbook evidence.
- The student is an **agent, not a viewer**.
- The voice tells; the textbook-grounded explanation is a separate layer (section 8).
- Narration language and dialect are configurable (`DIALECTS.md`) and never change the teaching rules.

---

## 2. A scene is a story event, not a concept card

Every scene must answer seven questions:

1. What exact concept or objective is being taught?
2. What must the student see?
3. Why is that visual necessary?
4. What can the student do?
5. What changes when they act?
6. What should they understand afterwards?
7. What changes in the story, and what question makes them want to continue?

Every scene declares:

| Field | Meaning |
|---|---|
| `story.function` | Its role in the story: setup, discovery, investigation, learner_decision, resolution... |
| `story.event` | The specific event |
| `story.character_goal` | The character's current goal |
| `story.conflict` | The obstacle or open question |
| `story.learning_opportunity` | The objective-constrained discovery (not a lecture topic) |
| `story.continuity_from_previous` | The causal bridge from the previous scene |
| `student_role` | The student's role and agency |
| `consequence` | What happens after the action, and the visible result |

**Rejected scenes:** no event, no consequence for the student's action, or a fresh story started at a section boundary.

---

## 3. The lesson arc

One lesson is one connected story:

```text
Opening      an unresolved situation and an open question (never a summary)
Middle       each scene reveals the next evidence-based event
Pause        a real decision, prediction or experiment by the student
Next scene   shows the consequence of what the student did
Ending       resolves the opening question with a satisfying payoff
```

The lesson declares up front: `world`, `strategy`, `premise`, `character` (optional), `goal`, `conflict`, `stakes`, `progression`, `resolution`.

- A new lesson means a new story. **Never carry details or characters across lessons.**
- Use the fewest scenes that get from understanding to a real action or application.
- A scene boundary is a meaningful teaching move, not a paragraph break.

---

## 4. Learning model inside a lesson

Target sequence where it makes pedagogical sense:

```text
Observe  >  Predict / Manipulate  >  Consequence  >  Apply  >  Payoff
```

As a thinking loop: **Predict, Manipulate, Observe, Reflect.**

Five experience patterns, mapped to `story_strategy`:

| Pattern | Shape | Best for |
|---|---|---|
| Discover | observe, interact, discover | Science |
| Explore | change a variable, see different outcomes | Physics, math, probability |
| Predict | situation, prediction, reveal, explain | Science |
| Build / Solve | goal, student arranges objects, reaches the correct state | Math, physics |
| Follow a Process | step, interaction, step, result | Biology, chemistry, history |

### Allowed story strategies
`MYSTERY`, `CHALLENGE`, `MISSION`, `DISCOVERY`, `PROBLEM`, `PREDICTION`, `INVESTIGATION`, `JOURNEY`, `SIMULATION`, `CUSTOM`
(Any other value becomes `CUSTOM`; the default is `DISCOVERY`.)

**Vary the strategy between lessons.** Do not open every lesson with the same team or the same hidden object. A process or challenge can work well with no character at all.

---

## 5. Student role and interaction

### Student roles
`observer`, `explorer`, `helper`, `investigator`, `decision_maker`, `co_player`

- `agency = observe_and_infer`: follows and infers.
- `agency = choose_or_test`: chooses or experiments.

### Interaction rules (strict)
1. An interaction is a **causal story action**, not navigation.
2. It must change **declared state** and produce a **visible consequence** that moves the story forward.
3. **Never** use an interaction as a disguised "next" button, as decoration, or only to make a narrated thing appear.
4. Changes tied to the narration happen automatically with the speech. The student pauses only for a **real decision, prediction or experiment**.
5. The object in the artwork is the input surface (no buttons laid over the drawing).
6. The server validates the outcome; the client is never trusted.

Allowed types:
`click`, `hotspot`, `reveal`, `drag`, `drop`, `drag_drop`, `select`, `match`, `sequence`, `position`, `rotate`, `slider`, `predict`, `choice`, `numeric_input`, `text_input`, `visual_model`

### The "why?" test for every interaction
```text
Objective > Concept > Student action > Observable change > Expected insight
```
**If you cannot fill all five, remove the interaction.** Interaction has a cognitive cost.

### Real example (friction lesson)
Salma has set up the experiment and the result is still hidden. The student touches the two surfaces one at a time. The system waits until two distinct surfaces were touched, then shows the cart's path on each, and the comparison becomes possible.

---

## 6. Narration: anticipation, event, discovery

For every spoken sentence:
- **Before** the event: a hint or anticipation ("but a tiny mark cracked it open from below").
- The **event** appears in the visual in sync with the words.
- **After** the event: a reaction, a question or an inference.

Hard rules:
- Never state the result before it appears.
- Every spoken sentence has a matching visual step.
- Ordered processes (growth, stages): show only the stage reached, never reveal the next one, never reset one that already happened.
- Opening scene: a situation and an open question only. No summary.

---

## 7. State drives progression

The student's actions move declared state inside the lesson's limits:

```text
S0 --(student acts)--> S1 --(changes a factor)--> S2 --> result --> next scene
```

Real example: `growth_stage` from 0 to 6 and `growth_phase` (seed, root_emerges, cotyledons, ...). Each scene reads `state_before` and writes `state_after`, which keeps the story from jumping or going backwards.

---

## 8. The three text layers of a scene

Each scene stores its texts separately. All three describe **the same scene state** and rest on **the same evidence**:

| Field | Job | Voice |
|---|---|---|
| `caption` | Short text that orients the student | Neutral, short |
| `explanation` | Simple, textbook-grounded explanation | Educational, tied to passage ids |
| `voice_script` / `story_script` | The spoken storytelling | The persona (narrator) |

**The voice is narration, not the source of truth.** Truth comes from the evidence-linked explanation. This is exactly why the persona has `teaching_role = false`.

In every dialect, captions, explanations and labels follow the textbook's wording (simple MSA for Arabic, plain English for English).

---

## 9. Grounding and safety

- Every educational claim must point to real `evidence_passage_ids`.
- Curriculum text and KG labels are **untrusted data**, not instructions (protection against prompt injection inside the text).
- Never invent objectives, KG nodes, facts or prerequisites.
- No student data is sent to the model.
- Mathematical and scientific accuracy comes from deterministic models, not generated images.
- The LLM plans; code computes.

---

## 10. Adaptivity (policy defined, not yet active)

| When | Do |
|---|---|
| Incorrect answer | Give a hint grounded in the evidence |
| Repeated incorrect answers | Recommend an earlier scene for the same objective |
| Mastery shown | Continue the story |

It activates once a per-session learning-evidence store exists (`active: false` today). Events collected: `response`, `error`, `hint`, `retry`, `time`, `modality`, `mastery`, `interaction_behavior`.

---

## 11. Narrative QA checklist

### Scene level
- [ ] A story event exists (`story_event_present`)
- [ ] The student has a role and a purpose (`learner_has_a_role`)
- [ ] The action has a consequence (`action_has_consequence`)
- [ ] The scene continues the previous one, except the first (`scene_continues_story`)
- [ ] Learning is a constraint: `learning_opportunity` plus `objective_ids` (`learning_is_a_constraint`)
- [ ] A scene visual plan exists (`scene_visual_plan_exists`)

### Lesson level
- [ ] World declared
- [ ] Goal and conflict declared
- [ ] Resolution declared
- [ ] Scenes form a causal chain
- [ ] Every scene has a student role and a consequence
- [ ] The final scene is marked as the payoff (`is_lesson_payoff`)

These are structural checks. Factual correctness is checked by semantic and source QA.

---

## 12. Worked example: plant growth (4 scenes, strategy MYSTERY)

| # | Event | Conflict / question | Role |
|---|---|---|---|
| 1 | A mysterious mark near Maryam's seed | Who started moving under the soil? | investigator |
| 2 | The root makes its way | What moved first, the root or the leaf? | investigator |
| 3 | The first two leaves | Are those all the leaves there will be? | investigator |
| 4 | New leaves change the scene | What is new after the first two leaves? | investigator |

Each scene starts from the result of the previous one (continuity). State advances (`growth_stage` 0, 1, 2, 3). The persona's state accumulates (`discovered_node_ids`). Curriculum facts (root first, seed leaves before true leaves) appear as **events**, not as definitions.

---

## 13. Summary for the team

1. Story leads; objectives constrain it.
2. A scene is an event, not an explanation card.
3. The student is an agent: every interaction passes the "why?" test and has a visible consequence.
4. Narration: anticipation, event, discovery. Never burn the result.
5. Truth comes from the textbook and KG; the persona only tells.
6. A lesson is one connected story with a full arc and a payoff.
7. Dialect is a setting, not a design decision: one dialect per lesson, chosen in `dialect_profiles.json`.

# Dialect Options

Narration can be generated in four configurable options. The teaching method and the persona rules are identical in all of them; only the *language of the learner-facing text* changes.

| Option id | Label | Code | Direction | Aliases accepted |
|---|---|---|---|---|
| `egyptian` | Egyptian Arabic (colloquial) | `ar-EG` | rtl | egyptian, egypt, eg, masri, ar-eg |
| `saudi` | Saudi Arabic (white dialect) | `ar-SA` | rtl | saudi, ksa, sa, khaleeji, ar-sa |
| `msa` | Modern Standard Arabic (simple, spoken-style) | `ar` | rtl | msa, fusha, standard, modern_standard_arabic, ar |
| `english` | English | `en` | ltr | english, en, en-us, en-gb |

Default option: `msa` (change `"default"` in `dialect_profiles.json`).

## How to select a dialect

```python
from persona_engine import build_persona
from prompt_builder import build_prompt

dialect = "saudi"   # "egyptian" | "saudi" | "msa" | "english"

system  = build_prompt("story_sequence_planner", dialect=dialect)
persona = build_persona(outline, previous_scene, dialect=dialect)
```

- Pass the same `dialect` to every prompt and every `build_persona` call of a lesson.
- Invalid values raise a clear `ValueError`.
- To tune a dialect (vocabulary to prefer or avoid, instructions), edit `dialect_profiles.json`. No code change is needed.

## What the dialect controls

| Text | Follows the selected dialect? |
|---|---|
| Narration (`story_script`, `voice_script`) | Yes |
| Character dialogue | Yes |
| Captions, explanations, visual labels | **No.** They stay in simple MSA (for Arabic options) or plain English, matching the textbook wording |
| Technical terms, units, numbers | **No.** Always exactly as in the textbook |
| JSON keys and enum values | **No.** Always English |
| Persona metadata (identity, voice, relationship) | **No.** English instruction data for the LLM |

This split matters: the Saudi curriculum is written in Modern Standard Arabic, so explanations must stay aligned with the textbook even when the story voice is colloquial.

## Shared rules (all options)

- **terminology**: Technical terms, labels, units and numbers must always match the textbook exactly, whatever dialect is selected.
- **student_address_arabic**: Arabic imperatives are gendered. Prefer gender-neutral phrasing (plural or 'let's' style, for example: خلّينا نجرّب / لنجرّب) instead of guessing the learner's gender. If the product knows the learner's gender, pass it explicitly as an input.
- **student_address_english**: Address the learner as 'you'.
- **consistency**: Use one dialect per lesson. Do not mix dialects inside a lesson or a scene.
- **json_keys**: JSON keys and enum values stay in English. Only learner-facing string values use the selected language.

## Egyptian Arabic (colloquial)

**Narration instruction:** Write all spoken narration (story_script, voice_script) and character dialogue in natural colloquial Egyptian Arabic, the way a warm storyteller speaks aloud to a 9-10 year old.

**Captions and explanations:** Write captions, explanations and visual labels in simple Modern Standard Arabic that matches the textbook wording. Do not use dialect in them.

**Prefer:**

- Demonstratives: ده / دي / دول
- Question words: إيه، ليه، إزاي، فين، مين
- Future with ه: هشوف، هنجرّب
- Everyday particles: دلوقتي، كده، بس، خلاص، تاني

**Avoid:**

- Gulf markers: وش، ليش، شلون، الحين
- Levantine markers: شو، هلق، كتير
- Heavy slang or idioms a 9-10 year old may not know

**Review status:** Sample narration for this dialect comes from the project's real demo output.

**Sample: plant growth, opening scene**

> زرعت مريم بذرة صغيرة في أصيص الشباك، وكانت متأكدة إنها هتشوف نبتة كبيرة الصبح. رجعت تاني يوم، فالتراب كان ساكت… لكن علامة صغيرة شقته من تحت. بصّت مريم وهمست: «مين بدأ يتحرك هناك؟»

**Sample: friction, opening scene**

> كان ممر المدرسة هاديًا، وفجأة سمعت سلمى خشخشة عربة لعبتها. على الأرض أثران: واحد طويل والتاني أقصر. قالت: «أنا دفعت العربة… بس ليه ما كملتش نفس المسافة؟»

## Saudi Arabic (white dialect)

**Narration instruction:** Write all spoken narration (story_script, voice_script) and character dialogue in natural colloquial Saudi 'white' dialect: neutral and widely understood across the Kingdom, without a strong regional (Najdi, Hijazi, Southern) accent or slang.

**Captions and explanations:** Write captions, explanations and visual labels in simple Modern Standard Arabic that matches the textbook wording. Do not use dialect in them.

**Prefer:**

- Question words: وش، ليش، كيف، وين، منو
- Everyday particles: كذا، الحين، بكرة، ثاني يوم، مرّة (as intensifier)
- Future with ب: بتشوف، بنجرّب
- Negation with ما + verb: ما لقت، ما مشت

**Avoid:**

- Egyptian markers: ده، دي، إيه، إزاي، دلوقتي، كده، عايز
- Levantine markers: شو، هلق، كتير
- Strong regional slang or tribal/regional idioms

**Review status:** Sample narration for this dialect was authored by an AI model. Have a native Saudi educator review it before it is used as a reference.

**Sample: plant growth, opening scene**

> زرعت مريم بذرة صغيرة في الأصيص عند الشباك، وكانت متأكدة إنها بكرة بتشوف نبتة كبيرة. رجعت ثاني يوم، والتراب ساكت… بس علامة صغيرة شقّته من تحت. قربت مريم وهمست: «وش اللي يتحرك هناك؟»

**Sample: friction, opening scene**

> كان ممر المدرسة هادي، وفجأة سمعت سلمى صوت عربتها اللعبة. على الأرض أثرين: واحد طويل وواحد أقصر. قالت: «أنا دفعت العربة… بس ليش ما مشت نفس المسافة؟»

## Modern Standard Arabic (simple, spoken-style)

**Narration instruction:** Write all narration (story_script, voice_script) and character dialogue in simple, warm Modern Standard Arabic: short sentences, concrete verbs, everyday vocabulary and a natural storytelling rhythm. No dialect words and no heavy classical or literary vocabulary.

**Captions and explanations:** Write captions, explanations and visual labels in simple Modern Standard Arabic that matches the textbook wording.

**Prefer:**

- Short sentences of about 8-14 words
- Active, concrete verbs
- Simple dialogue verbs: قال، همست، سأل، ابتسم
- Light use of diacritics, only where meaning could be ambiguous

**Avoid:**

- Any colloquial words (ده، وش، ليش، إيه ...)
- Rare classical vocabulary
- Long chains of subordinate clauses
- Lecture connectors such as: ومن الجدير بالذكر

**Review status:** Sample narration for this dialect was authored by an AI model; review wording against the target grade.

**Sample: plant growth, opening scene**

> زرعت مريم بذرة صغيرة في أصيص النافذة، وكانت واثقة أنها سترى نبتة كبيرة في الصباح. وفي اليوم التالي بدا التراب ساكنًا… لكن علامة صغيرة شقّته من تحته. اقتربت مريم وهمست: «من الذي بدأ يتحرك هناك؟»

**Sample: friction, opening scene**

> كان ممر المدرسة هادئًا، وفجأة سمعت سلمى صوت عربتها اللعبة. على الأرض أثران: أحدهما طويل والآخر أقصر. قالت: «دفعتُ العربة… فلماذا لم تقطع المسافة نفسها؟»

## English

**Narration instruction:** Write all narration (story_script, voice_script) and character dialogue in simple, warm, spoken-style English for a 9-10 year old: short sentences, concrete verbs, contractions allowed.

**Captions and explanations:** Write captions, explanations and visual labels in plain English that matches the textbook wording.

**Prefer:**

- Short sentences
- Concrete, sensory verbs
- Contractions (it's, didn't, she'd)
- Simple dialogue tags: said, whispered, asked

**Avoid:**

- Idioms and slang a child may not know
- Academic connectors such as: therefore, thus, moreover
- Lecture openers such as: Today we will learn

**Review status:** Sample narration for this dialect was authored by an AI model.

**Sample: plant growth, opening scene**

> Maryam planted a tiny seed in the pot by the window, sure she'd see a big plant by morning. The next day the soil sat perfectly still… but a tiny mark had cracked it open from underneath. Maryam leaned in and whispered, "Who's moving down there?"

**Sample: friction, opening scene**

> The school hallway was quiet, until Salma heard her toy cart rattle. Two marks lay on the floor: one long, one short. "I pushed it the same way," she said. "So why didn't it go as far?"

## Adding a new dialect

1. Add an entry under `dialects` in `dialect_profiles.json` with the same fields (`id`, `label`, `language_code`, `direction`, `narration`, `captions_explanations`, `prefer`, `avoid`, `review_note`, `sample_narration`).
2. Add its aliases under `aliases`.
3. Run the checks below.

## Quick check

```bash
python3 -c "from prompt_builder import build_prompt; print(build_prompt('scene_compiler', 'saudi')[-900:])"
```

## Recommended QA for dialects

- A native educator reviews each dialect's samples before they are used as references.
- Automated check: `persona.dialect` is the same in all scenes of a lesson.
- Automated check: a Saudi lesson contains none of the avoid-list Egyptian markers (and the reverse).
- Spot-check that captions and explanations did not drift into dialect.

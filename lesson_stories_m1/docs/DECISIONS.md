# DECISIONS (Module 1)

- **Function names**: `s0_intake.run`, `s1_brief.run`, `s1_brief.validate_brief_dict`, `pipeline.run_module1`.
- **Tests use `unittest`** (stdlib) so nothing needs installing; pytest also runs them unchanged.
- **FakeLLM / CountingFakeLLM** live in `tests/unit/helpers.py` (test-only code, not in the package).
- **LLM interface**: one method, `complete_json(task, prompt, payload) -> dict`; tasks `topic_locator`, `brief`, `brief_review`.
- **Request shape (Section 3 not available)**: `lesson_id, lesson_text, topic{topic_id,title,text}, country, language, dialect, age_group, grade, subject, target_duration_sec`.
- **Age ranges**: only 9-11 (default 150, range 120-210) is from the spec. 6-8 (90/120/150) and 12-14 (150/210/300) are ASSUMED. Edit `config.AGE_GROUPS`.
- **Error codes** added beyond the spec: `INVALID_REQUEST` (S0), `BRIEF_INVALID`, `BRIEF_REVIEW_FLAGGED` (S1). Stages raise `PipelineError(code)`; the orchestrator sets the version to `failed`.
- **`topic.text` given**: used as-is; `prior_text` / `later_preview` are filled only if that text can be found inside `lesson_text`, otherwise they are empty.
- **Span end** includes closing punctuation right after the end quote (so the final period is kept).
- **Retries**: S1 makes up to 3 attempts; blockers and reviewer flags are fed back to the LLM as `feedback`. A malformed reviewer answer counts as a flag.
- **Cache**: SQLite table `brief_cache(cache_key, brief_json, created_at, expires_at)`; key = `COUNTRY|language|dialect-or-none|age_group`; TTL 90 days.
- **MSA** is always accepted even if the TTS provider's list does not contain it.

# Lesson Stories - Module 1 (S0 Intake + S1 Localization Brief)

```
src/lesson_stories/
  config.py       numbers and lookup tables (limits, age ranges, country->dialect, TTL)
  errors.py       ErrorCode + PipelineError
  models.py       Request, Intake (intake.json), Brief (brief.json)
  llm.py          LLMClient protocol - plug your real small-model client here
  prompts.py      prompt builders (topic locator, brief, reviewer)
  text_utils.py   normalize_text, norm_ar, find_span
  s0_intake.py    S0
  cache.py        SQLite brief cache
  s1_brief.py     S1
  pipeline.py     run_module1 = S0 -> S1, writes the two JSON artifacts
tests/unit/       helpers.py (FakeLLM) + 3 test files
tests/fixtures/   sample_request.json + llm/*.json canned answers
scripts/demo.py   runs the golden sample and writes out/intake.json, out/brief.json
```

Run the tests: `./run_tests.sh`  (or `python3 -m unittest discover -s tests/unit -v`, or `pytest`)
Run the demo:  `python3 scripts/demo.py`

To go live, implement `LLMClient.complete_json` with your model and pass it as `llm`.

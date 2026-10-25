"""Runs Module 1 end to end: every function, then the full pipeline.

    python3 main.py                  # offline, fake LLM answers (no API key needed)
    python3 main.py --real           # real LLM (needs `pip install anthropic` + ANTHROPIC_API_KEY)
    python3 main.py --request my_request.json --out out
"""
import argparse
import json
import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests" / "unit"))

from lesson_stories import s0_intake, s1_brief                       # noqa: E402
from lesson_stories.cache import BriefCache, make_key, utcnow        # noqa: E402
from lesson_stories.errors import PipelineError                      # noqa: E402
from lesson_stories.pipeline import run_module1                      # noqa: E402
from lesson_stories.text_utils import find_span, norm_ar, normalize_text  # noqa: E402

# ----------------------------------------------------------------- your settings
TTS_SUPPORTED_DIALECTS = ["gulf", "msa"]   # dialects your TTS provider supports
TTS_PROVIDER_NAME = "groq"
REAL_MODEL = "claude-haiku-5-5"


def title(text):
    print(f"\n{'=' * 8} {text} {'=' * 8}")


class RealLLM:
    """Real client behind the LLMClient interface (complete_json -> dict)."""

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic()

    def complete_json(self, task, prompt, payload):
        msg = self.client.messages.create(
            model=REAL_MODEL, max_tokens=4000,
            messages=[{"role": "user",
                       "content": prompt + "\n\nINPUT:\n" + json.dumps(payload, ensure_ascii=False)}])
        text = msg.content[0].text.strip()
        text = text.removeprefix("```json").removesuffix("```").strip()
        return json.loads(text)


def make_llm(real):
    if real:
        return RealLLM()
    from helpers import FakeLLM   # canned answers from tests/fixtures/llm
    return FakeLLM(["s0_topic_locator.json", "s1_brief.json"], reviewer="s1_review_clean.json")


def demo_text_utils(request):
    title("text_utils")
    print("normalize_text :", repr(normalize_text("a\u00a0b\n\n\n\nc")))
    print("norm_ar        :", norm_ar("قُسم، إليها."))
    text = normalize_text(request["lesson_text"])
    span = find_span(text, "مفهوم الكسر الكسر جزء من كل عندما", "ونكتب ذلك 1/4")
    print("find_span      :", span, "->", text[span[0]:span[0] + 25] + "...")


def demo_s0_helpers(request):
    title("S0 helpers")
    print("script_ratio(ar):", round(s0_intake.script_ratio(request["lesson_text"], "ar"), 2))
    print("derive_dialect  :", {c: s0_intake.derive_dialect(c) for c in ("EG", "SA", "JO", "MA", "JP")})
    print("resolve_dialect :", s0_intake.resolve_dialect("ar", "EG", None, TTS_SUPPORTED_DIALECTS, TTS_PROVIDER_NAME))
    print("resolve_duration:", [s0_intake.resolve_duration("9-11", v) for v in (None, 400, 60)])


def demo_s0_run(request, llm):
    title("S0 run")
    intake = s0_intake.run(request, TTS_SUPPORTED_DIALECTS, llm, TTS_PROVIDER_NAME)
    print("topic chars :", len(intake.topic_text))
    print("prior_text  :", intake.prior_text)
    print("later       :", intake.later_preview[:30] + "...")
    print("dialect     :", intake.dialect_applied, "| warnings:", [w.code for w in intake.warnings])
    print("duration    :", intake.target_duration_sec)
    return intake


def demo_s1(intake, llm):
    title("S1 brief")
    db = sqlite3.connect(":memory:")
    key = make_key(intake.country, intake.language, intake.dialect_applied, intake.age_group)
    print("cache key   :", key)
    brief = s1_brief.run(intake.country, intake.language, intake.dialect_applied, intake.age_group, llm, db)
    print("validate    :", s1_brief.validate_brief_dict(brief.to_dict()) or "no problems")
    print("brief       :", len(brief.names_female), "female names,", len(brief.names_male), "male names,",
          len(brief.currency.typical_prices), "prices")
    calls_before = llm.calls
    s1_brief.run(intake.country, intake.language, intake.dialect_applied, intake.age_group, llm, db)
    print("2nd call    : LLM calls used =", llm.calls - calls_before, "(0 means served from cache)")
    print("cache valid :", BriefCache(db).get(key, utcnow()) is not None)


def demo_errors(request, llm_factory):
    title("error handling")
    cases = {
        "TOPIC_NOT_FOUND": lambda r: r["topic"].update(title="x") or r.update(lesson_text="كلام قصير جدا"),
        "LANGUAGE_MISMATCH": lambda r: r.update(language="en"),
        "INPUT_TOO_SHORT": lambda r: r["topic"].update(text="كسر " * 20),
    }
    for expected, mutate in cases.items():
        r = json.loads(json.dumps(request))
        mutate(r)
        try:
            s0_intake.run(r, TTS_SUPPORTED_DIALECTS, llm_factory())
            print(f"{expected:18}: no error (unexpected)")
        except PipelineError as e:
            print(f"{expected:18}: caught -> {e.code}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", action="store_true", help="use the real LLM instead of fake answers")
    ap.add_argument("--request", default=str(ROOT / "tests" / "fixtures" / "sample_request.json"))
    ap.add_argument("--out", default=str(ROOT / "out"))
    args = ap.parse_args()

    request = json.loads(pathlib.Path(args.request).read_text(encoding="utf-8"))

    demo_text_utils(request)
    demo_s0_helpers(request)
    intake = demo_s0_run(request, make_llm(args.real))
    demo_s1(intake, make_llm(args.real))
    demo_errors(request, lambda: make_llm(False))

    title("full pipeline (run_module1)")
    intake, brief = run_module1(request, TTS_SUPPORTED_DIALECTS, make_llm(args.real),
                                sqlite3.connect(":memory:"), out_dir=pathlib.Path(args.out))
    print("written:", args.out + "/intake.json", "and", args.out + "/brief.json")
    print("done.")


if __name__ == "__main__":
    try:
        main()
    except PipelineError as e:
        print(f"\nPipeline failed: {e.code} - {e.message}")
        sys.exit(1)

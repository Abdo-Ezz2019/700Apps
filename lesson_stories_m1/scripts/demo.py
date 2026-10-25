"""Run Module 1 on the golden sample with fake LLM answers and print intake.json / brief.json."""
import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests" / "unit"))

from helpers import FakeLLM, load  # noqa: E402
from lesson_stories.pipeline import run_module1  # noqa: E402

out = ROOT / "out"
llm = FakeLLM(["s0_topic_locator.json", "s1_brief.json"], reviewer="s1_review_clean.json")
intake, brief = run_module1(load("sample_request.json"), ["gulf", "msa"], llm,
                            sqlite3.connect(":memory:"), out_dir=out)
print("dialect:", intake.dialect_applied, "| warnings:", [w.code for w in intake.warnings])
print("topic chars:", len(intake.topic_text), "| duration:", intake.target_duration_sec)
print("names:", len(brief.names_female), len(brief.names_male), "| written to", out)

import copy
import sqlite3
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

import helpers
from helpers import CountingFakeLLM, FakeLLM, load, load_llm
from lesson_stories import pipeline, s1_brief
from lesson_stories.cache import BriefCache, make_key, utcnow
from lesson_stories.errors import ErrorCode, PipelineError

KEY = dict(country="EG", language="ar", dialect_applied="msa", age_group="9-11")


class S1Base(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")

    def tearDown(self):
        self.db.close()

    def rows(self):
        return self.db.execute("SELECT cache_key FROM brief_cache").fetchall()


class TestS1(S1Base):
    def test_s1_brief_valid_and_cached(self):
        brief = s1_brief.run(**KEY, llm=FakeLLM("s1_brief.json", reviewer="s1_review_clean.json"), db=self.db)
        self.assertTrue(len(brief.names_female) >= 20 and len(brief.names_male) >= 20)
        self.assertEqual(len(brief.currency.typical_prices), 6)
        self.assertTrue(len(brief.places) >= 8 and len(brief.foods) >= 6)
        self.assertEqual(len(brief.speech_style.example_phrases), 5)
        llm2 = CountingFakeLLM()
        again = s1_brief.run(**KEY, llm=llm2, db=self.db)
        self.assertEqual(llm2.calls, 0)
        self.assertEqual(again.to_dict(), brief.to_dict())

    def test_count_too_low_retries_with_feedback(self):
        bad = load_llm("s1_brief.json")
        bad["names_female"] = bad["names_female"][:15]
        llm = FakeLLM([bad, "s1_brief.json"], reviewer="s1_review_clean.json")
        brief = s1_brief.run(**KEY, llm=llm, db=self.db)
        self.assertEqual(llm.count("brief"), 2)
        first_fb, second_fb = [p["feedback"] for t, p in llm.call_log if t == "brief"]
        self.assertEqual(first_fb, [])
        self.assertTrue(any("names_female" in f for f in second_fb))
        self.assertTrue(len(brief.names_female) >= 20)

    def test_count_too_low_forever_fails(self):
        bad = load_llm("s1_brief.json")
        bad["names_female"] = bad["names_female"][:15]
        llm = FakeLLM(bad, reviewer="s1_review_clean.json")
        with self.assertRaises(PipelineError) as cm:
            s1_brief.run(**KEY, llm=llm, db=self.db)
        self.assertEqual(cm.exception.code, ErrorCode.BRIEF_INVALID)
        self.assertEqual(llm.count("brief"), 3)
        self.assertEqual(llm.count("brief_review"), 0)  # blockers stop before the reviewer
        self.assertEqual(self.rows(), [])  # nothing cached

    def test_reviewer_flags_then_passes(self):
        llm = FakeLLM("s1_brief.json", reviewer=["s1_review_flagged.json", "s1_review_clean.json"])
        s1_brief.run(**KEY, llm=llm, db=self.db)
        self.assertEqual(llm.count("brief"), 2)
        second_fb = [p["feedback"] for t, p in llm.call_log if t == "brief"][1]
        self.assertTrue(any("real brand" in f for f in second_fb))

    def test_reviewer_flags_forever_fails(self):
        llm = FakeLLM("s1_brief.json", reviewer="s1_review_flagged.json")
        with self.assertRaises(PipelineError) as cm:
            s1_brief.run(**KEY, llm=llm, db=self.db)
        self.assertEqual(cm.exception.code, ErrorCode.BRIEF_REVIEW_FLAGGED)
        self.assertEqual(self.rows(), [])

    def test_malformed_reviewer_answer_counts_as_flag(self):
        llm = FakeLLM("s1_brief.json", reviewer={"oops": 1})
        with self.assertRaises(PipelineError) as cm:
            s1_brief.run(**KEY, llm=llm, db=self.db)
        self.assertEqual(cm.exception.code, ErrorCode.BRIEF_REVIEW_FLAGGED)

    def test_cache_expiry_regenerates(self):
        old = utcnow() - timedelta(days=100)  # stored with a 90-day TTL -> expired 10 days ago
        s1_brief.run(**KEY, llm=FakeLLM("s1_brief.json", reviewer="s1_review_clean.json"), db=self.db, now=old)
        llm = FakeLLM("s1_brief.json", reviewer="s1_review_clean.json")
        s1_brief.run(**KEY, llm=llm, db=self.db)
        self.assertEqual(llm.count("brief"), 1)

    def test_cache_not_expired_inside_ttl(self):
        recent = utcnow() - timedelta(days=89)
        s1_brief.run(**KEY, llm=FakeLLM("s1_brief.json", reviewer="s1_review_clean.json"), db=self.db, now=recent)
        llm = CountingFakeLLM()
        s1_brief.run(**KEY, llm=llm, db=self.db)
        self.assertEqual(llm.calls, 0)

    def test_different_dialect_separate_row(self):
        for dialect in ("msa", "egyptian"):
            s1_brief.run(country="EG", language="ar", dialect_applied=dialect, age_group="9-11",
                         llm=FakeLLM("s1_brief.json", reviewer="s1_review_clean.json"), db=self.db)
        self.assertEqual(len(self.rows()), 2)
        self.assertNotEqual(make_key("EG", "ar", "msa", "9-11"), make_key("EG", "ar", "egyptian", "9-11"))

    def test_english_key_has_no_dialect(self):
        self.assertEqual(make_key("US", "en", None, "9-11"), "US|en|none|9-11")


class TestValidator(unittest.TestCase):
    def test_good_fixture_is_valid(self):
        self.assertEqual(s1_brief.validate_brief_dict(load_llm("s1_brief.json")), [])

    def test_each_blocker(self):
        cases = {
            "typical_prices": lambda d: d["currency"].__setitem__("typical_prices", d["currency"]["typical_prices"][:5]),
            "example_phrases": lambda d: d["speech_style"].__setitem__("example_phrases", ["a"] * 4),
            "places": lambda d: d.__setitem__("places", d["places"][:7]),
            "foods": lambda d: d.__setitem__("foods", d["foods"][:5]),
            "transport": lambda d: d.__setitem__("transport", d["transport"][:2]),
            "holidays_and_seasons": lambda d: d.__setitem__("holidays_and_seasons", d["holidays_and_seasons"][:3]),
            "sensitivities": lambda d: d.__setitem__("sensitivities", d["sensitivities"][:2]),
            "names_male": lambda d: d.__setitem__("names_male", d["names_male"][:19]),
            "humor_notes": lambda d: d.__setitem__("humor_notes", "جملة. وجملة. وثالثة."),
            "currency": lambda d: d.__delitem__("currency"),
        }
        for name, mutate in cases.items():
            with self.subTest(field=name):
                d = load_llm("s1_brief.json")
                mutate(d)
                problems = s1_brief.validate_brief_dict(d)
                self.assertTrue(any(name in p for p in problems), problems)

    def test_not_an_object(self):
        self.assertEqual(s1_brief.validate_brief_dict([1, 2]), ["brief must be a JSON object"])


class TestIntegration(S1Base):
    def test_module1_end_to_end_writes_artifacts(self):
        llm = FakeLLM(["s0_topic_locator.json", "s1_brief.json"], reviewer="s1_review_clean.json")
        with tempfile.TemporaryDirectory() as tmp:
            intake, brief = pipeline.run_module1(load("sample_request.json"), ["gulf", "msa"],
                                                 llm, self.db, out_dir=Path(tmp))
            self.assertTrue((Path(tmp) / "intake.json").exists())
            self.assertTrue((Path(tmp) / "brief.json").exists())
        self.assertEqual(intake.dialect_applied, "msa")
        # S1 used the dialect actually applied by S0, so the cache key carries 'msa'
        self.assertEqual(self.rows(), [(make_key("EG", "ar", "msa", "9-11"),)])
        self.assertEqual(len(brief.names_female) >= 20, True)


if __name__ == "__main__":
    unittest.main()

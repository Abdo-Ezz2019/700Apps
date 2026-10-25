import copy
import unittest

import helpers
from helpers import CountingFakeLLM, FakeLLM, load
from lesson_stories import s0_intake
from lesson_stories.errors import ErrorCode, PipelineError

ALL_DIALECTS = ["egyptian", "gulf", "levantine", "maghrebi", "msa"]


def arabic_text(n):
    """Arabic filler of exactly n chars that does not end with a space."""
    return " ".join(["كسر"] * 200)[:n].rstrip()


def req_with(**changes):
    r = load("sample_request.json")
    for k, v in changes.items():
        if k == "topic_text":
            r["topic"]["text"] = v
        else:
            r[k] = v
    return r


class TestS0Golden(unittest.TestCase):
    def test_s0_golden(self):
        out = s0_intake.run(request=load("sample_request.json"),
                            tts_supported_dialects=["gulf", "msa"],
                            llm=FakeLLM("s0_topic_locator.json"))
        self.assertTrue(out.topic_text.startswith("مفهوم الكسر"))
        self.assertTrue(out.topic_text.rstrip(".").endswith("1/4"))
        self.assertTrue(300 <= len(out.topic_text) <= 450)
        self.assertTrue(out.later_preview.startswith("مقارنة الكسور"))
        self.assertNotIn("مقارنة الكسور", out.topic_text)
        self.assertEqual(out.prior_text, "الكسور")
        self.assertEqual(out.dialect_applied, "msa")
        self.assertEqual([w.code for w in out.warnings], ["DIALECT_FALLBACK"])
        self.assertEqual(out.target_duration_sec, 150)
        self.assertEqual((out.grade, out.subject, out.country), ("4", "math", "EG"))

    def test_to_dict_has_all_artifact_keys(self):
        out = s0_intake.run(load("sample_request.json"), ["gulf", "msa"], FakeLLM("s0_topic_locator.json"))
        self.assertEqual(list(out.to_dict()), [
            "topic_title", "topic_text", "prior_text", "later_preview", "language", "dialect_applied",
            "country", "age_group", "grade", "subject", "target_duration_sec", "warnings"])


class TestS0Cases(unittest.TestCase):
    def run_s0(self, req, dialects=("gulf", "msa"), llm=None):
        return s0_intake.run(req, list(dialects), llm or FakeLLM("s0_topic_locator.json"))

    def test_topic_text_given_skips_locator(self):
        text = arabic_text(250)
        llm = CountingFakeLLM()
        out = self.run_s0(req_with(topic_text=text), llm=llm)
        self.assertEqual(llm.calls, 0)
        self.assertEqual(out.topic_text, text)

    def test_topic_not_found(self):
        llm = FakeLLM({"start_quote": "كلام غير موجود في الدرس نهائيا", "end_quote": "ولا هذا أيضا ابدا"})
        with self.assertRaises(PipelineError) as cm:
            self.run_s0(load("sample_request.json"), llm=llm)
        self.assertEqual(cm.exception.code, ErrorCode.TOPIC_NOT_FOUND)

    def test_topic_not_found_malformed_locator(self):
        with self.assertRaises(PipelineError) as cm:
            self.run_s0(load("sample_request.json"), llm=FakeLLM({}))
        self.assertEqual(cm.exception.code, ErrorCode.TOPIC_NOT_FOUND)

    def test_too_short(self):
        with self.assertRaises(PipelineError) as cm:
            self.run_s0(req_with(topic_text=arabic_text(120)), llm=CountingFakeLLM())
        self.assertEqual(cm.exception.code, ErrorCode.INPUT_TOO_SHORT)

    def test_language_mismatch(self):
        with self.assertRaises(PipelineError) as cm:
            self.run_s0(req_with(language="en"))
        self.assertEqual(cm.exception.code, ErrorCode.LANGUAGE_MISMATCH)

    def test_english_ok_and_no_dialect(self):
        text = ("Fractions describe equal parts of a whole. When we split a pizza into four equal pieces "
                "and eat one piece, we ate one quarter of the pizza, written as 1/4. The top number is the "
                "numerator and the bottom number is the denominator.")
        out = self.run_s0(req_with(language="en", topic_text=text), llm=CountingFakeLLM())
        self.assertIsNone(out.dialect_applied)
        self.assertEqual(out.warnings, [])

    def test_egyptian_supported(self):
        out = self.run_s0(load("sample_request.json"), dialects=["egyptian", "msa"])
        self.assertEqual(out.dialect_applied, "egyptian")
        self.assertEqual(out.warnings, [])

    def test_explicit_dialect(self):
        out = self.run_s0(req_with(dialect="gulf"))
        self.assertEqual(out.dialect_applied, "gulf")
        self.assertEqual(out.warnings, [])

    def test_explicit_dialect_unsupported_falls_back(self):
        out = self.run_s0(req_with(dialect="levantine"))
        self.assertEqual(out.dialect_applied, "msa")
        self.assertEqual([w.code for w in out.warnings], ["DIALECT_FALLBACK"])
        self.assertIn("requested", out.warnings[0].message)

    def test_unknown_dialect_rejected(self):
        with self.assertRaises(PipelineError) as cm:
            self.run_s0(req_with(dialect="klingon"))
        self.assertEqual(cm.exception.code, ErrorCode.INVALID_REQUEST)

    def test_country_map(self):
        for country, expected in [("SA", "gulf"), ("JO", "levantine"), ("MA", "maghrebi"),
                                  ("JP", "msa"), ("EG", "egyptian"), ("AE", "gulf")]:
            with self.subTest(country=country):
                out = self.run_s0(req_with(country=country), dialects=ALL_DIALECTS)
                self.assertEqual(out.dialect_applied, expected)
                self.assertEqual(out.warnings, [])

    def test_duration_clamp(self):
        for requested, expected in [(400, 210), (60, 120), (180, 180), (None, 150)]:
            with self.subTest(requested=requested):
                out = self.run_s0(req_with(target_duration_sec=requested))
                self.assertEqual(out.target_duration_sec, expected)

    def test_diacritics_insensitive_quotes(self):
        # lesson has "شيئًا" and "إلى"; quotes are written without diacritics / with other alef
        llm = FakeLLM({"start_quote": "عندما نقسم شيئا الى اجزاء متساوية",
                       "end_quote": "فقد أكلنا ربع البيتزا ونكتب ذلك 1/4"})
        out = self.run_s0(load("sample_request.json"), llm=llm)
        self.assertTrue(out.topic_text.startswith("عندما نقسم شيئًا"))

    def test_invalid_age_group(self):
        with self.assertRaises(PipelineError) as cm:
            self.run_s0(req_with(age_group="40-50"))
        self.assertEqual(cm.exception.code, ErrorCode.INVALID_REQUEST)

    def test_missing_fields(self):
        r = load("sample_request.json")
        del r["country"]
        with self.assertRaises(PipelineError) as cm:
            self.run_s0(r)
        self.assertEqual(cm.exception.code, ErrorCode.INVALID_REQUEST)

    def test_topic_text_given_not_in_lesson_has_empty_context(self):
        out = self.run_s0(req_with(topic_text=arabic_text(250)), llm=CountingFakeLLM())
        self.assertEqual((out.prior_text, out.later_preview), ("", ""))

    def test_context_limits(self):
        r = load("sample_request.json")
        r["lesson_text"] = ("كلمة " * 1000) + "\n\n" + r["lesson_text"] + "\n\n" + ("بعد " * 500)
        out = self.run_s0(r)
        self.assertLessEqual(len(out.prior_text), 2500)
        self.assertLessEqual(len(out.later_preview), 400)


if __name__ == "__main__":
    unittest.main()

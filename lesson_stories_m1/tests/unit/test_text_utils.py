import unittest

import helpers  # noqa: F401  (sets sys.path)
from lesson_stories.text_utils import find_span, norm_ar, normalize_text


class TestNormalize(unittest.TestCase):
    def test_nbsp_and_newlines(self):
        self.assertEqual(normalize_text("a\u00a0b\n\n\n\nc"), "a b\n\nc")

    def test_nfc(self):
        self.assertEqual(normalize_text("e\u0301"), "\u00e9")

    def test_keeps_diacritics(self):
        self.assertEqual(normalize_text("شيئًا"), "شيئًا")


class TestNormAr(unittest.TestCase):
    def test_strips_diacritics_and_punctuation(self):
        self.assertEqual(norm_ar("قُسم، إليها."), norm_ar("قسم اليها"))

    def test_digits_and_case(self):
        self.assertEqual(norm_ar("١/٤ ABC"), "1 4 abc")


class TestFindSpan(unittest.TestCase):
    TEXT = "مقدمة. قُسِّمَ الكلُّ إلى أجزاءٍ متساوية، ثم أخذنا جزءًا واحدًا. خاتمة أخرى."

    def test_span_with_trailing_period(self):
        s, e = find_span(self.TEXT, "قسم الكل الى اجزاء", "اخذنا جزءا واحدا")
        self.assertTrue(self.TEXT[s:e].startswith("قُسِّمَ"))
        self.assertTrue(self.TEXT[s:e].endswith("واحدًا."))

    def test_missing_quote(self):
        self.assertIsNone(find_span(self.TEXT, "غير موجود", "اخذنا"))

    def test_end_before_start(self):
        self.assertIsNone(find_span(self.TEXT, "خاتمة اخرى", "مقدمة"))

    def test_empty_quotes(self):
        self.assertIsNone(find_span(self.TEXT, "", ""))


if __name__ == "__main__":
    unittest.main()

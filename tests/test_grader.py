import unittest

from ielts_tts.grader import accepted, band, grade, normalise


class Grader(unittest.TestCase):
    def test_case_and_articles(self):
        self.assertEqual(normalise("The Museum"), "museum")

    def test_optional_and_alternatives(self):
        keys = accepted("23(rd) March | March 23(rd)")
        for given in ["23 March", "23rd march", "March 23rd", "march 23"]:
            self.assertIn(normalise(given), keys)
        self.assertIn(normalise("waterproof jackets"), accepted("waterproof jacket(s)"))

    def test_numbers_as_words(self):
        self.assertIn(normalise("seven"), accepted("7"))
        self.assertIn(normalise("15"), accepted("fifteen"))

    def test_spelling_must_be_exact(self):
        result = grade({"1": "Whitfield"}, {"1": "Whitefield"})
        self.assertFalse(result["results"]["1"]["correct"])

    def test_blank_is_wrong(self):
        self.assertEqual(grade({"1": "a"}, {})["score"], 0)

    def test_choose_two_any_order(self):
        answers = {"21": "B, D", "22": "B, D"}
        self.assertEqual(grade(answers, {"21": "D", "22": "b"}, [[21, 22]])["score"], 2)
        self.assertEqual(grade(answers, {"21": "B", "22": "B"}, [[21, 22]])["score"], 1)

    def test_letters_on_one_line(self):
        self.assertTrue(grade({"5": "A, C"}, {"5": "c a"})["results"]["5"]["correct"])

    def test_times(self):
        self.assertIn(normalise("9.30 a.m."), accepted("9.30 am"))

    def test_band_table(self):
        self.assertEqual(band(40), 9.0)
        self.assertEqual(band(30), 7.0)
        self.assertEqual(band(23), 6.0)
        self.assertIsNone(band(8, total=10))

    def test_results_sorted_numerically(self):
        result = grade({"10": "x", "2": "y"}, {})
        self.assertEqual(list(result["results"]), ["2", "10"])


if __name__ == "__main__":
    unittest.main()


class WordLimits(unittest.TestCase):
    def test_rubric_parsing(self):
        from ielts_tts.grader import word_limit
        self.assertEqual(word_limit("Write ONE WORD AND/OR A NUMBER for each answer."), {"words": 1, "number": True})
        self.assertEqual(word_limit("Write ONE WORD ONLY for each answer."), {"words": 1, "number": False})
        self.assertEqual(word_limit("Write NO MORE THAN TWO WORDS for each answer."), {"words": 2, "number": False})
        self.assertEqual(word_limit("Write A NUMBER for each answer."), {"words": 0, "number": True})
        self.assertIsNone(word_limit("Choose the correct letter, A, B or C."))

    def test_codes_count_as_one_number(self):
        from ielts_tts.grader import count_words
        self.assertEqual(count_words("GL5 3TB"), (0, 1))
        self.assertEqual(count_words("23rd March"), (1, 1))
        self.assertEqual(count_words("well-known shop"), (2, 0))

    def test_over_limit_is_wrong_and_tallies_by_type(self):
        sets = [{"start": 1, "end": 2, "type": "note", "limit": {"words": 1, "number": False}},
                {"start": 3, "end": 3, "type": "mcq", "limit": None}]
        result = grade({"1": "jacket", "2": "lagoon", "3": "B"},
                       {"1": "waterproof jacket", "2": "Lagoon", "3": "b"}, sets=sets)
        self.assertFalse(result["results"]["1"]["correct"])
        self.assertEqual(result["results"]["1"]["reason"], "over the word limit")
        self.assertTrue(result["results"]["2"]["correct"])
        self.assertTrue(result["results"]["3"]["correct"])
        self.assertEqual(result["by_type"], {"note": [1, 2], "mcq": [1, 1]})
        self.assertEqual(result["by_part"], {"1": [2, 3]})

    def test_letter_answers_need_exactly_one_letter(self):
        sets = [{"start": 11, "end": 11, "type": "map", "limit": None}]
        self.assertFalse(grade({"11": "D"}, {"11": "D E"}, sets=sets)["results"]["11"]["correct"])

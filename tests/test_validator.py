import unittest
from pathlib import Path

from ielts_tts.parser import detect_task, parse_test
from ielts_tts.validator import validate

LIBRARY = Path(__file__).resolve().parent.parent / "library"


def problems(script, kind):
    result = validate(parse_test(script, kind), kind)
    return [i["text"] for i in result["items"] if i["level"] == "error"], result


GOOD_PART4 = """### PART 4
Title: Part 4 – Bees
Narrator: Part 4. You will hear a lecture about bees.
Narrator: First, you have some time to look at questions 31 to 40.
[Pause 45]
Narrator: Now listen carefully and answer questions 31 to 40.
Lecturer: Bees build hives from wax and collect pollen and nectar from flowers across the valley.
Narrator: That is the end of Part 4.
=== QUESTIONS ===
@SET 31-40 | note | Complete the notes below. Write ONE WORD ONLY for each answer.
""" + "\n".join(f"– item {n} ________".replace("item", f"fact {n}") for n in range(31, 41)).replace("fact", "note") + """
=== ANSWERS ===
""" + "\n".join(f"{n}. word{n}" for n in range(31, 41))


class LibrarySamples(unittest.TestCase):
    def test_every_sample_passes_with_no_errors(self):
        for f in sorted(LIBRARY.glob("*.txt")):
            test = parse_test(f.read_text(encoding="utf-8"))
            kind = detect_task(test)
            result = validate(test, kind)
            errors = [i["text"] for i in result["items"] if i["level"] == "error"]
            self.assertNotEqual(kind, "custom", f.name)
            self.assertEqual(errors, [], f.name)

    def test_full_test_has_40_questions_and_four_parts(self):
        test = parse_test((LIBRARY / "full-test-1.txt").read_text(encoding="utf-8"), "full")
        self.assertEqual(test.question_numbers, list(range(1, 41)))
        self.assertEqual([p["n"] for p in test.parts], [1, 2, 3, 4])
        self.assertEqual(len(test.sets), len({(s["start"], s["end"]) for s in test.sets}))


class Errors(unittest.TestCase):
    def test_wrong_part_for_page(self):
        errors, _ = problems(GOOD_PART4, "part2")
        self.assertTrue(any("This page is for Part 2" in e for e in errors))

    def test_missing_answer_and_numbering(self):
        script = GOOD_PART4.replace("40. word40", "").replace("40 ________", "")
        errors, _ = problems(script, "part4")
        self.assertTrue(any("no answer for question(s) 40" in e for e in errors), errors)

    def test_answer_over_word_limit(self):
        errors, _ = problems(GOOD_PART4.replace("31. word31", "31. sea water"), "part4")
        self.assertTrue(any("breaks the word limit" in e and "Q31" in e for e in errors), errors)

    def test_optional_words_and_alternatives_respect_limit(self):
        errors, _ = problems(GOOD_PART4.replace("31. word31", "31. (the) hive(s) | colony"), "part4")
        self.assertEqual(errors, [])

    def test_unknown_type_and_missing_sets(self):
        errors, _ = problems(GOOD_PART4.replace("| note |", "| gapfill |"), "part4")
        self.assertTrue(any("unknown question type" in e for e in errors), errors)
        errors, _ = problems(GOOD_PART4.replace("@SET 31-40 | note | ", ""), "part4")
        self.assertTrue(any("no @SET headers" in e for e in errors), errors)

    def test_mid_lecture_break_warns(self):
        script = GOOD_PART4.replace("Narrator: That is the end of Part 4.",
                                    "[Pause 30]\nLecturer: Moving on.\nNarrator: That is the end of Part 4.")
        _, result = problems(script, "part4")
        self.assertTrue(any("no break in the middle" in i["text"] for i in result["items"] if i["level"] == "warn"))

    def test_mcq_answer_outside_options(self):
        script = """### PART 3
Narrator: Part 3. You will hear two students.
Tom: Hi.
Ann: Hello.
=== QUESTIONS ===
@SET 21-30 | mcq | Choose the correct letter, A, B or C.
""" + "\n".join(f"{n}. Question?\nA  one\nB  two\nC  three" for n in range(21, 31)) + """
=== ANSWERS ===
""" + "\n".join(f"{n}. {'D' if n == 21 else 'B'}" for n in range(21, 31))
        errors, _ = problems(script, "part3")
        self.assertTrue(any("not among the options" in e for e in errors), errors)

    def test_custom_page_never_blocks(self):
        result = validate(parse_test("Sam: Hello\nAnn: Hi", "custom"), "custom")
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()

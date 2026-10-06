import unittest
from pathlib import Path

from ielts_tts.parser import NARRATOR, parse, parse_test, pause_seconds

SAMPLE = (Path(__file__).resolve().parent.parent / "library" / "part1-harbourview-bike-tours.txt").read_text(encoding="utf-8")


class SampleScript(unittest.TestCase):
    def setUp(self):
        self.test = parse_test(SAMPLE, "part1")

    def test_title_and_speakers(self):
        self.assertEqual(self.test.title, "Part 1 – Harbourview Bike Tours")
        self.assertEqual(self.test.speakers, ["Sam", "Clara"])
        self.assertEqual(self.test.voice_overrides["Clara"], "bf_emma")

    def test_narrator_lines(self):
        narrated = [s.text for s in self.test.segments if s.speaker == NARRATOR]
        self.assertEqual(narrated[0], "Part 1. You will hear a woman phoning a bike tour company to book a tour.")
        self.assertIn("Before you hear the rest of the conversation, you have some time to look at questions 7 to 10.",
                      narrated)
        self.assertEqual(narrated[-1], "That is the end of Part 1.")

    def test_reading_time_pauses(self):
        pauses = [s for s in self.test.segments if s.kind == "pause"]
        self.assertEqual([p.seconds for p in pauses], [30, 30])

    def test_questions_answers_and_sets(self):
        self.assertEqual(self.test.question_numbers, list(range(1, 11)))
        self.assertEqual(self.test.answers["1"], "Whitfield")
        self.assertEqual([(s["start"], s["end"], s["type"]) for s in self.test.sets], [(1, 6, "form"), (7, 10, "note")])
        self.assertEqual(self.test.sets[0]["limit"], {"words": 1, "number": True})
        self.assertEqual(self.test.warnings, [])

    def test_part_marker_is_not_read_aloud(self):
        self.assertFalse(any("PART" in s.text for s in self.test.segments))
        self.assertEqual(parse(SAMPLE).title, "Part 1 – Harbourview Bike Tours")


class LegacyFormat(unittest.TestCase):
    def test_v1_announced_pause(self):
        t = parse("You will hear a call.\nSam: Hi\n[Pause: you now have 30 seconds to look at questions 7 to 10.]\nSam: Bye")
        kinds = [(s.kind, s.speaker, s.seconds) for s in t.segments]
        self.assertEqual(kinds, [("speech", NARRATOR, 0), ("speech", "Sam", 0), ("speech", NARRATOR, 0),
                                 ("pause", "", 30), ("speech", "Sam", 0)])


class Formats(unittest.TestCase):
    def test_markdown_and_titles(self):
        t = parse("**Dr Lee:** Good morning.\n**Student A:** Hi.\nMrs Brown (landlady): Welcome.")
        self.assertEqual(t.speakers, ["Dr Lee", "Student A", "Mrs Brown"])
        self.assertEqual(t.segments[0].text, "Good morning.")

    def test_not_speakers(self):
        t = parse("Note: this is a note\nQuestions 1-5 are below")
        self.assertEqual(t.speakers, [])

    def test_unlabelled_lecture_paragraphs_continue_speaker(self):
        t = parse("You will hear a lecture about bees.\nLecturer: Good morning.\nToday we look at bees.\n"
                  "Before you hear the rest of the talk, you have some time to look at questions 35 to 40.")
        speakers = [s.speaker for s in t.segments]
        self.assertEqual(speakers, [NARRATOR, "Lecturer", "Lecturer", NARRATOR])

    def test_voices_override(self):
        t = parse("Voices: Sam=bm_lewis, Narrator=bf_lily\nSam: Hi")
        self.assertEqual(t.voice_overrides, {"Sam": "bm_lewis", NARRATOR: "bf_lily"})

    def test_silence_only_pause(self):
        t = parse("A: Hi\n[Pause 5]\n[Pause: thirty seconds]\nA: Bye")
        kinds = [(s.kind, s.seconds) for s in t.segments]
        self.assertEqual(kinds, [("speech", 0), ("pause", 5), ("pause", 30), ("speech", 0)])

    def test_choose_two_range(self):
        t = parse("A: Hi\n=== QUESTIONS ===\n21-22 Which TWO...\n=== ANSWERS ===\n21-22. B, D\n23. C")
        self.assertEqual(t.answer_groups, [[21, 22]])
        self.assertEqual(t.answers["22"], "B, D")

    def test_pause_seconds(self):
        self.assertEqual(pause_seconds("look at questions 7 to 10. You have 30 seconds"), 30)
        self.assertEqual(pause_seconds("thirty seconds"), 30)
        self.assertEqual(pause_seconds("two minutes"), 120)
        self.assertEqual(pause_seconds("some time"), 5)
        self.assertEqual(pause_seconds("first you have some time to look at questions 1 to 6"), 5)

    def test_announced_pause_without_duration_defaults_to_20s(self):
        t = parse("[Pause: first you have some time to look at questions 1 to 6.]\nA: Hi")
        self.assertEqual([(s.kind, s.seconds) for s in t.segments][:2], [("speech", 0), ("pause", 20)])


if __name__ == "__main__":
    unittest.main()


class MultiPart(unittest.TestCase):
    def test_parse_full_test(self):
        from ielts_tts.parser import parse_test
        script = (Path(__file__).resolve().parent.parent / "library" / "full-test-1.txt").read_text(encoding="utf-8")
        t = parse_test(script, "full")
        self.assertEqual(t.kind, "full")
        self.assertEqual({s.part for s in t.segments}, {1, 2, 3, 4})
        self.assertTrue(t.title.startswith("Full Test 1"))
        self.assertIn("map", {s["type"] for s in t.sets})

    def test_missing_transitions_are_added(self):
        from ielts_tts.parser import parse_test
        script = "### PART 1\nA: Hi\nB: Hello\n### PART 2\nGuide: Welcome\n### PART 3\nA: x\n### PART 4\nL: y"
        t = parse_test(script, "full")
        auto = [s for s in t.segments if s.auto]
        self.assertEqual(len([s for s in auto if s.kind == "pause"]), 3)
        self.assertIn("That is the end of Part 1", auto[0].text)

    def test_outer_code_fence_is_ignored(self):
        from ielts_tts.parser import parse_test
        t = parse_test("```text\n### PART 2\nGuide: Hello there\n```", "part2")
        self.assertEqual([s.text for s in t.segments], ["Hello there"])

    def test_tilde_fence_contents_are_not_questions(self):
        from ielts_tts.parser import parse_test
        t = parse_test("Guide: Hi\n=== QUESTIONS ===\n@SET 15-16 | map | Label the map below. Write the correct letter, A–E, next to Questions 15–16.\n~~~\n 12. not a question ________\n~~~\n15. Cafe ________\n16. Shop ________\n=== ANSWERS ===\n15. A\n16. B", "part2")
        self.assertEqual(t.question_numbers, [15, 16])


class CheckingTime(unittest.TestCase):
    def test_turn_to_next_part_after_pause_gets_no_second_pause(self):
        from ielts_tts.parser import parse_test
        part = lambda n: (f"### PART {n}\nA: Hello {n}\nNarrator: That is the end of Part {n}. You now have half a minute "
                          f"to check your answers.\n[Pause 30]\nNarrator: Now turn to Part {n + 1}.\n")
        t = parse_test(part(1) + part(2) + part(3) + "### PART 4\nL: Lecture.\n", "full")
        self.assertEqual([s.seconds for s in t.segments if s.kind == "pause"], [30, 30, 30])
        self.assertFalse(any(s.auto for s in t.segments))

    def test_missing_pause_is_added_right_after_the_announcement(self):
        from ielts_tts.parser import parse_test
        t = parse_test("### PART 1\nA: Hi\nNarrator: That is the end of Part 1.\nNarrator: Now turn to Part 2.\n"
                       "### PART 2\nB: Hello\n### PART 3\nC: x\n### PART 4\nD: y", "full")
        p1 = [(s.kind, s.text[:20]) for s in t.segments if s.part == 1]
        self.assertEqual(p1[2][0], "pause")
        self.assertEqual(p1[3][1], "Now turn to Part 2.")

    def test_final_checking_pause_is_dropped(self):
        from ielts_tts.parser import parse_test
        t = parse_test("### PART 4\nL: The end of my talk.\nNarrator: That is the end of Part 4. You now have two "
                       "minutes to check your answers.\n[Pause 120]", "part4")
        self.assertEqual([s.kind for s in t.segments], ["speech", "speech"])

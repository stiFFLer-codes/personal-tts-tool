import unittest
from pathlib import Path

from ielts_tts.parser import NARRATOR, parse, pause_seconds

SAMPLE = (Path(__file__).resolve().parent.parent / "library" / "part1-harbourview-bike-tours.txt").read_text(encoding="utf-8")


class SampleScript(unittest.TestCase):
    def setUp(self):
        self.test = parse(SAMPLE)

    def test_title_and_speakers(self):
        self.assertEqual(self.test.title, "Part 1 – Harbourview Bike Tours")
        self.assertEqual(self.test.speakers, ["Sam", "Clara"])

    def test_narrator_lines(self):
        narrated = [s.text for s in self.test.segments if s.speaker == NARRATOR]
        self.assertEqual(narrated[0], "You will hear a woman phoning a bike tour company to book a tour.")
        self.assertIn("You now have 30 seconds to look at questions 7 to 10.", narrated)
        self.assertEqual(narrated[-1], "That is the end of Part 1.")

    def test_pause_is_real_silence_after_announcement(self):
        pauses = [i for i, s in enumerate(self.test.segments) if s.kind == "pause"]
        self.assertEqual(len(pauses), 1)
        self.assertEqual(self.test.segments[pauses[0]].seconds, 30)
        self.assertEqual(self.test.segments[pauses[0] - 1].speaker, NARRATOR)

    def test_questions_and_answers(self):
        self.assertEqual(self.test.question_numbers, list(range(1, 11)))
        self.assertEqual(self.test.answers["1"], "Whitfield")
        self.assertEqual(self.test.warnings, [])

    def test_recording_script_header_not_read(self):
        self.assertFalse(any("Recording script" in s.text for s in self.test.segments))


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

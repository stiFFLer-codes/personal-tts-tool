import re
import unittest

from ielts_tts import prompt_builder as pb


class Prompts(unittest.TestCase):
    def test_every_task_builds_without_placeholders(self):
        for task in pb.TASKS:
            for note in ("", "Make it hard, with plenty of map questions."):
                prompt = pb.build(task, note)["prompt"]
                self.assertNotRegex(prompt, r"\{\{\w+\}\}")
                self.assertIn("STRICT OUTPUT FORMAT", prompt)
                self.assertIn("Never write the name of the exam anywhere in your output", prompt)
                self.assertIn("```text", prompt)

    def test_claude_decides_the_content(self):
        prompt = pb.build("part2")["prompt"]
        self.assertIn("WHAT IS UP TO YOU", prompt)
        self.assertIn("do not fall back on one fixed template", prompt)
        # No prescribed plans, topics or difficulty any more.
        self.assertNotRegex(prompt, r"QUESTION PLAN|TOPIC / SITUATION|DIFFICULTY \(")

    def test_numbering_per_task(self):
        self.assertIn("Number the questions 11–20", pb.build("part2")["prompt"])
        self.assertIn("Number the questions 31–40", pb.build("part4")["prompt"])
        full = pb.build("full")["prompt"]
        self.assertIn("all FOUR Parts", full)
        self.assertIn("31–40 in Part 4", full)

    def test_note_is_included_and_trimmed(self):
        prompt = pb.build("part1", "  more\nspelling   questions ")["prompt"]
        self.assertIn('"more spelling questions"', prompt)
        self.assertNotIn("The learner adds", pb.build("part1")["prompt"])
        long = pb.build("part1", "x" * 5000)["prompt"]
        self.assertLess(len(long), len(pb.build("part1")["prompt"]) + pb.MAX_NOTE + 200)

    def test_unknown_task(self):
        with self.assertRaises(ValueError):
            pb.build("part9")


if __name__ == "__main__":
    unittest.main()

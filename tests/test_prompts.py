import re
import unittest

from ielts_tts import prompt_builder as pb
from ielts_tts.grader import word_limit
from ielts_tts.parser import SET_TYPES


class Prompts(unittest.TestCase):
    def test_every_task_and_focus_builds_without_placeholders(self):
        for task in pb.TASKS:
            for focus in [f["id"] for f in pb.focus_options(task)]:
                for difficulty in pb.DIFFICULTY:
                    for accent in ("british", "mixed"):
                        result = pb.build(task, focus=focus, difficulty=difficulty, accent=accent, seed=1)
                        self.assertNotRegex(result["prompt"], r"\{\{\w+\}\}")
                        self.assertIn("STRICT OUTPUT FORMAT", result["prompt"])

    def test_plans_cover_each_part_exactly(self):
        ranges = {"part1": (1, 10), "part2": (11, 20), "part3": (21, 30), "part4": (31, 40)}
        for task, plans in pb.PLANS.items():
            for name, plan in plans.items():
                for p in plan if isinstance(plan, list) else [plan]:
                    covered = [n for s in p["sets"] for n in range(s["start"], s["end"] + 1)]
                    self.assertEqual(covered, list(range(*ranges[task])) + [ranges[task][1]], (task, name))
                    for s in p["sets"]:
                        self.assertIn(s["type"], SET_TYPES)
                        letters = s["type"] in {"mcq", "mcq-multi", "matching", "map"} or "letter" in s["rubric"]
                        self.assertTrue(letters or word_limit(s["rubric"]), (task, name, s["rubric"]))
                    if task == "part4":
                        self.assertIsNone(p["split"])

    def test_focus_drill_uses_only_that_type(self):
        prompt = pb.build("part2", focus="map", seed=2)["prompt"]
        headers = re.findall(r"Header: @SET \S+ \| (\S+) \|", prompt)
        self.assertEqual(set(headers), {"map"})

    def test_full_test_has_four_parts_and_linking_narration(self):
        prompt = pb.build("full", seed=3)["prompt"]
        for n in range(1, 5):
            self.assertIn(f"█████ PART {n}", prompt)
        self.assertIn("You now have half a minute to check your answers.\n[Pause 30]", prompt)
        self.assertIn("Narrator: Now turn to Part 2.", prompt)
        self.assertIn("That is the end of the Listening test.", prompt)

    def test_official_rubrics(self):
        self.assertEqual(pb.matching_rubric(11, 16),
                         "Choose SIX answers from the box and write the correct letter, A–H, next to Questions 11–16.")
        self.assertEqual(pb.map_rubric(15, 20), "Label the map below. Write the correct letter, A–I, next to Questions 15–20.")

    def test_topic_bank(self):
        topics = pb.topics()
        for task in ("part1", "part2", "part3", "part4"):
            self.assertGreaterEqual(len(topics[task]), 25)
        self.assertIn(pb.random_topic("part1"), topics["part1"])


if __name__ == "__main__":
    unittest.main()

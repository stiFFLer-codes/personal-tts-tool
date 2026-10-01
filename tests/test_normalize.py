import unittest

from ielts_tts.normalize import for_speech, speech_parts


class Normalize(unittest.TestCase):
    def test_spelled_name_split_into_letters(self):
        parts = speech_parts("No, there's no E. It's W-H-I-T-F-I-E-L-D.")
        self.assertEqual(parts[0], ("text", "No, there's no E. It's"))
        self.assertEqual(parts[1], ("letters", list("WHITFIELD")))

    def test_hyphenated_words_untouched(self):
        self.assertEqual(for_speech("the twenty-third, a well-known under-fives deal"),
                         "the twenty-third, a well-known under-fives deal")

    def test_phone_number_digit_by_digit(self):
        self.assertEqual(for_speech("Call 0412 556 789."), "Call oh four one two, five five six, seven eight nine.")

    def test_years_and_counts_unchanged(self):
        self.assertEqual(for_speech("In 1998, 1,200 people came."), "In 1998, 1,200 people came.")

    def test_money(self):
        self.assertEqual(for_speech("It's £42.50 or £1."), "It's 42 pounds 50 or 1 pound.")
        self.assertEqual(for_speech("Only $15.99"), "Only 15 dollars and 99 cents")

    def test_times(self):
        self.assertEqual(for_speech("at 9:00 or 9:05 or 9:30"), "at 9 o'clock or 9 oh 5 or 9 30")

    def test_stage_directions_removed(self):
        self.assertEqual(for_speech("[laughs] **Well** (sighs) OK"), "Well OK")


if __name__ == "__main__":
    unittest.main()

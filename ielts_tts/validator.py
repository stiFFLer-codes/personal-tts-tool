"""Check a parsed script against the real IELTS Listening format before rendering.

Returns a checklist the Studio shows as ✅ / ⚠️ / ❌. Errors block "Generate" on the
task pages (the script would make a broken test); warnings are things a real
paper would do differently but that still produce a usable practice test.
"""

import re

from . import grader
from .normalize import has_spelling
from .parser import NARRATOR, PART_RANGES, SET_TYPES, Test

# Speech words per Part (narration excluded). Real recordings run ~4-7 minutes.
WORDS = {1: (450, 1100), 2: (450, 1100), 3: (450, 1150), 4: (500, 1200)}
SPEAKERS = {1: (2, 2), 2: (1, 2), 3: (2, 4), 4: (1, 1)}
TASK_PARTS = {"part1": [1], "part2": [2], "part3": [3], "part4": [4], "full": [1, 2, 3, 4]}


class Checklist:
    def __init__(self):
        self.items = []

    def add(self, level, text):
        self.items.append({"level": level, "text": text})

    def ok(self, text):
        self.add("ok", text)

    def warn(self, text):
        self.add("warn", text)

    def error(self, text):
        self.add("error", text)

    def check(self, condition, good, bad, level="error"):
        self.add("ok", good) if condition else self.add(level, bad)
        return condition

    @property
    def errors(self):
        return [i for i in self.items if i["level"] == "error"]


def _set_block(questions: str, qset: dict) -> str:
    """The lines of the question paper belonging to one @SET (up to the next @SET)."""
    lines = questions.splitlines()
    start = next((i for i, l in enumerate(lines) if re.match(rf"\s*@SET\s+{qset['start']}\b", l, re.I)), None)
    if start is None:
        return ""
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"\s*@SET\b", lines[i], re.I)), len(lines))
    return "\n".join(lines[start:end])


def _option_letters(block: str) -> set:
    """Letters offered in a set: 'A  text' option lines, 'A–H' ranges, letters on a text map."""
    letters = {m.group(1) for m in re.finditer(r"^\s*([A-L])[.)]?\s{1,}\S", block, re.M)}
    for m in re.finditer(r"\b([A-L])\s*[–-]\s*([A-L])\b", block):
        letters |= {chr(c) for c in range(ord(m.group(1)), ord(m.group(2)) + 1)}
    return letters


def _check_part(c: Checklist, test: Test, part: int, info: dict, strict: bool):
    label = f"Part {part}"
    lo, hi = PART_RANGES[part]
    expected = list(range(lo, hi + 1))
    numbers = info["numbers"]
    c.check(numbers == expected, f"{label}: questions {lo}–{hi} (10 questions)",
            f"{label}: needs questions {lo}–{hi}, found {_fmt(numbers) or 'none'}")

    missing = [n for n in expected if str(n) not in test.answers]
    c.check(not missing, f"{label}: answer key complete",
            f"{label}: no answer for question(s) {_fmt(missing)}")

    sets = info["sets"]
    level = "error" if strict else "warn"
    if not c.check(bool(sets), f"{label}: {len(sets)} question set(s) tagged with @SET",
                   f"{label}: no @SET headers, so question types and word limits are unknown", level):
        return
    unknown = [s["type"] for s in sets if not s["known"]]
    c.check(not unknown, f"{label}: question types recognised ({', '.join(sorted({s['type'] for s in sets}))})",
            f"{label}: unknown question type(s) {', '.join(unknown)}; use one of {', '.join(SET_TYPES)}")
    covered = {n for s in sets for n in range(s["start"], s["end"] + 1)}
    uncovered = [n for n in expected if n not in covered]
    c.check(not uncovered, f"{label}: every question belongs to a set",
            f"{label}: question(s) {_fmt(uncovered)} are not inside any @SET range", "warn")

    for s in sets:
        block = _set_block(info["questions"], s)
        rng = f"Q{s['start']}–{s['end']}" if s["end"] != s["start"] else f"Q{s['start']}"
        letters = s["type"] in grader.LETTER_TYPES or re.search(r"\bletters?\b", s["rubric"], re.I)
        if letters:
            offered = _option_letters(block)
            keys = [test.answers.get(str(n), "") for n in range(s["start"], s["end"] + 1)]
            bad = [k for k in keys if k and not set(grader._letters(k)) <= offered] if offered else []
            if not offered:
                c.warn(f"{label} {rng}: couldn't find the lettered options (A, B, C...) for this {s['type']} set")
            elif bad:
                c.error(f"{label} {rng}: answer(s) {', '.join(bad)} not among the options {''.join(sorted(offered))}")
            if any(k and not grader._letters(k) for k in keys):
                c.error(f"{label} {rng}: {SET_TYPES.get(s['type'], s['type'])} answers must be letters")
            if s["type"] == "map" and not re.search(r"^\s*(?:~~~|```)", block, re.M):
                c.warn(f"{label} {rng}: map/plan set has no ~~~ text map")
        else:
            if not s["limit"]:
                c.warn(f"{label} {rng}: rubric has no word limit (e.g. 'Write ONE WORD AND/OR A NUMBER for each answer.')")
                continue
            over = []
            for n in range(s["start"], s["end"] + 1):
                for option in grader.options(test.answers.get(str(n), "")):
                    if not grader.within_limit(grader.required_part(option), s["limit"]):
                        over.append(f"Q{n} '{option}'")
            c.check(not over, f"{label} {rng}: answers fit '{_limit_text(s['limit'])}'",
                    f"{label} {rng}: answer key breaks the word limit: {', '.join(over)}")


def _check_audio(c: Checklist, test: Test, part: int):
    label = f"Part {part}"
    segs = [s for s in test.segments if s.part == part and not s.auto]
    speech = [s for s in segs if s.kind == "speech"]
    voices = []
    for s in speech:
        if s.speaker != NARRATOR and s.speaker not in voices:
            voices.append(s.speaker)
    lo, hi = SPEAKERS[part]
    kinds = {1: "two speakers", 2: "one main speaker", 3: "2–4 speakers", 4: "one lecturer"}
    c.check(lo <= len(voices) <= hi, f"{label}: {len(voices)} speaker(s), as in the real test ({kinds[part]})",
            f"{label}: has {len(voices)} speaker(s) ({', '.join(voices) or 'none'}); real Part {part} has {kinds[part]}",
            "warn")

    words = sum(len(s.text.split()) for s in speech if s.speaker != NARRATOR)
    wlo, whi = WORDS[part]
    c.check(wlo <= words <= whi, f"{label}: {words} words of speech (real: ~{wlo}–{whi})",
            f"{label}: {words} words of speech; real Part {part} recordings have ~{wlo}–{whi}", "warn")

    intro = next((s for s in speech), None)
    c.check(bool(intro and intro.speaker == NARRATOR), f"{label}: opens with the narrator's introduction",
            f"{label}: should open with a narrator line ('You will hear...')", "warn")

    pauses = [i for i, s in enumerate(segs) if s.kind == "pause"]
    first_talk = next((i for i, s in enumerate(segs) if s.kind == "speech" and s.speaker != NARRATOR), len(segs))
    reading_time = [i for i in pauses if i < first_talk]
    c.check(bool(reading_time), f"{label}: reading time before the first questions",
            f"{label}: no [Pause: ...] before the recording starts (time to look at the questions)", "warn")
    last_talk = max((i for i, s in enumerate(segs) if s.kind == "speech" and s.speaker != NARRATOR), default=0)
    mid = [i for i in pauses if first_talk < i < last_talk]
    if part == 4:
        c.check(not mid, f"{label}: no break in the middle of the lecture (as in the real test)",
                f"{label}: the real Part 4 has no break in the middle of the lecture; remove the mid-lecture [Pause]",
                "warn")
    else:
        c.check(bool(mid), f"{label}: break before the second block of questions",
                f"{label}: real Parts 1–3 pause halfway ('Before you hear the rest...') for the next questions",
                "warn")

    if part == 1:
        c.check(any(has_spelling(s.text) for s in speech), f"{label}: includes a spelled-out name or word",
                f"{label}: real Part 1 usually spells a name letter by letter (W-H-I-T-F-I-E-L-D)", "warn")


def _limit_text(limit):
    words = {0: "", 1: "ONE WORD", 2: "NO MORE THAN TWO WORDS", 3: "NO MORE THAN THREE WORDS",
             4: "NO MORE THAN FOUR WORDS"}[limit["words"]]
    if limit["number"]:
        return f"{words} AND/OR A NUMBER" if words else "A NUMBER"
    return f"{words} ONLY" if limit["words"] == 1 else words


def _fmt(nums):
    if not nums:
        return ""
    nums = sorted(nums)
    runs, start, prev = [], nums[0], nums[0]
    for n in nums[1:] + [None]:
        if n is not None and n == prev + 1:
            prev = n
            continue
        runs.append(f"{start}–{prev}" if prev != start else str(start))
        if n is not None:
            start = prev = n
    return ", ".join(runs)


def validate(test: Test, kind: str = None) -> dict:
    kind = kind or test.kind
    c = Checklist()
    speech = [s for s in test.segments if s.kind == "speech"]
    c.check(bool(speech), f"{len(speech)} spoken lines", "No spoken lines found ('Name: text' or narrator lines)")

    if kind in TASK_PARTS:
        wanted = TASK_PARTS[kind]
        found = [p["n"] for p in test.parts]
        if kind == "full":
            c.check(found == wanted, "Four Parts in order (### PART 1 … ### PART 4)",
                    f"A full test needs ### PART 1 to ### PART 4 in order (found: {', '.join(map(str, found)) or 'none'})")
        else:
            c.check(found == wanted, f"Script is a Part {wanted[0]} test",
                    f"This page is for Part {wanted[0]}, but the script looks like Part "
                    f"{', '.join(map(str, found)) or '?'} (check the question numbers)")
        for info in test.parts:
            if info["n"] in PART_RANGES:
                _check_part(c, test, info["n"], info, strict=True)
                _check_audio(c, test, info["n"])
        extra = [n for n in test.answers if int(n) not in
                 {q for p in test.parts for q in range(PART_RANGES.get(p["n"], (0, -1))[0],
                                                      PART_RANGES.get(p["n"], (0, -1))[1] + 1)}]
        c.check(not extra, "No stray answers", f"Answers for questions outside this test: {', '.join(extra)}", "warn")
        if kind == "full":
            auto = sum(1 for s in test.segments if s.auto and s.kind == "speech")
            if auto:
                c.warn(f"Added the standard 'That is the end of Part N…' + 30 s check after {auto} Part(s)")
            total = len(test.question_numbers)
            c.check(total == 40, "40 questions in total, so you get a band score",
                    f"{total} questions; a full test has 40")
    else:
        if test.question_numbers:
            missing = [n for n in test.question_numbers if str(n) not in test.answers]
            c.check(not missing, f"{len(test.question_numbers)} questions with an answer key",
                    f"No answer for question(s) {_fmt(missing)}", "warn")
        for qset in test.sets:
            if not qset["known"]:
                c.warn(f"Unknown question type '{qset['type']}'")

    for w in test.warnings:
        c.warn(w)
    return {"items": c.items, "errors": len(c.errors), "ok": not c.errors}

"""Parse a pasted IELTS listening script into something we can render and grade.

The format is deliberately forgiving so a script can be pasted straight from
Claude or a book. See docs/CLAUDE_SCRIPT_PROMPT.md for the full spec. In short::

    Title: Part 1 - Harbourview Bike Tours        (optional)
    Voices: Sam=bm_lewis, Clara=bf_emma           (optional)
    You will hear a woman phoning...              (no label -> Narrator)
    Sam: Good morning...                          (Name: text -> speaker)
    [Pause: you now have 30 seconds to look at questions 7 to 10.]
    === QUESTIONS ===
    1. Surname: ________
    === ANSWERS ===
    1. Whitfield
"""

import re
from dataclasses import dataclass, field, asdict

NARRATOR = "Narrator"

_NUMBER_WORDS = {
    "a": 1, "one": 1, "two": 2, "three": 3, "five": 5, "ten": 10, "fifteen": 15,
    "twenty": 20, "twenty-five": 25, "thirty": 30, "forty": 40, "forty-five": 45,
    "fifty": 50, "sixty": 60, "ninety": 90,
}

# Lines that open the script but shouldn't be read aloud.
_IGNORED_HEADERS = re.compile(
    r"^(recording script|transcript|audio ?script|tapescript|script)\s*:?\s*$", re.I)
_SECTION = re.compile(
    r"^[\s=#*-]*(questions?|answers?|answer key|key)\b[^a-z0-9]*$", re.I)
_TITLE = re.compile(r"^\s*(?:title\s*:|#)\s*(.+)$", re.I)
_VOICES = re.compile(r"^\s*voices?\s*:\s*(.+)$", re.I)
_PAUSE = re.compile(r"^\s*\[\s*pause\b\s*:?\s*(.*?)\s*\]\s*$", re.I)
# "Sam: ...", "Dr Lee: ...", "Student A: ...", "**Clara:** ..." , "Man (receptionist): ..."
_SPEAKER = re.compile(
    r"^\s*\**\s*([A-Z][\w.'-]*(?:\s[A-Z0-9][\w.'-]*){0,2})\s*(?:\([^)]{1,30}\))?\s*\**\s*:\s*\**\s*(.+)$")
_NOT_SPEAKERS = {
    "title", "voices", "voice", "note", "notes", "question", "questions", "answer",
    "answers", "example", "part", "section", "recording", "script", "transcript",
    "key", "instructions", "task", "tip", "warning", "source", "topic", "time",
}
# Narrator-style announcements that can appear mid-dialogue without a label.
_NARRATOR_CUES = re.compile(
    r"^(you will hear|you now have|now you will hear|now listen|now turn|listen carefully|"
    r"before you hear|first,? you have|look at questions|that is the end|this is the end|"
    r"you have (?:some|\d+|[a-z-]+ seconds)|now we shall|you should answer|"
    r"(?:part|section) (?:\d|one|two|three|four)\b)", re.I)
_ANSWER_LINE = re.compile(
    r"^\s*(\d{1,2})(?:\s*(?:-|–|&|and)\s*(\d{1,2}))?\s*[.):\-]?\s+(.+)$")
# "7. Why did..." at line start, or an inline numbered gap: "Name: Clara 1 ________"
_QUESTION_NUM = re.compile(r"^\s*(\d{1,2})\s*[.)]\s|(?<![\w£$€.,])(\d{1,2})\s*(?:_{2,}|…+|\.{4,})", re.M)


@dataclass
class Segment:
    kind: str            # "speech" | "pause"
    speaker: str = ""
    text: str = ""
    seconds: float = 0.0
    line: int = 0        # 1-based line in the pasted script


@dataclass
class Test:
    title: str = "Untitled test"
    segments: list = field(default_factory=list)
    speakers: list = field(default_factory=list)      # in order of appearance, Narrator excluded
    voice_overrides: dict = field(default_factory=dict)
    questions: str = ""
    answers: dict = field(default_factory=dict)       # "1" -> "Whitfield"
    answer_groups: list = field(default_factory=list) # [[21, 22]] for "choose TWO" questions
    warnings: list = field(default_factory=list)

    @property
    def question_numbers(self):
        nums = {int(m.group(1) or m.group(2)) for m in _QUESTION_NUM.finditer(self.questions)}
        return sorted(nums | {int(n) for n in self.answers})

    def to_dict(self):
        data = asdict(self)
        data["question_numbers"] = self.question_numbers
        data["has_narrator"] = any(s.speaker == NARRATOR for s in self.segments)
        return data


def pause_seconds(text: str, default: float = 5.0) -> float:
    """'you now have 30 seconds...' -> 30, 'thirty seconds' -> 30, '5' -> 5."""
    # Prefer a number with a unit ("30 seconds") over e.g. "questions 7 to 10".
    # A bare number only counts when it's the whole instruction: "[Pause 5]".
    m = (re.search(r"(\d+(?:\.\d+)?)\s*(?:sec|s\b|(min))", text, re.I)
         or re.fullmatch(r"\s*(\d+(?:\.\d+)?)()\s*", text))
    if not m:
        m = re.search(r"\b([a-z-]+)\s+(?:seconds?|(min)utes?)\b", text, re.I)
        if not m or m.group(1).lower() not in _NUMBER_WORDS:
            return default
        value = float(_NUMBER_WORDS[m.group(1).lower()])
    else:
        value = float(m.group(1))
    return value * 60 if m.group(2) else value


def _speaker_line(line: str):
    m = _SPEAKER.match(line)
    if not m:
        return None
    name, text = m.group(1).strip(), m.group(2).strip().strip("*").strip()
    if name.lower() in _NOT_SPEAKERS or re.fullmatch(r"\d+", name):
        return None
    if name.lower() == "narrator" or name.lower() == "announcer":
        name = NARRATOR
    return name, text


def parse(script: str) -> Test:
    test = Test()
    section = "script"
    question_lines, title_found = [], False
    last_speaker = None          # current non-narrator speaker, for unlabelled continuation lines

    for number, raw in enumerate(script.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue

        if _SECTION.match(line):
            section = "answers" if re.search(r"answer|key", line, re.I) else "questions"
            continue
        if section == "questions":
            question_lines.append(raw.rstrip())
            continue
        if section == "answers":
            m = _ANSWER_LINE.match(line)
            if m:
                first, last = int(m.group(1)), int(m.group(2) or m.group(1))
                for n in range(first, last + 1):
                    test.answers[str(n)] = m.group(3).strip()
                if last > first:
                    test.answer_groups.append(list(range(first, last + 1)))
            elif line:
                test.warnings.append(f"Line {number}: couldn't read answer '{line[:40]}'")
            continue

        if not title_found and (m := _TITLE.match(line)):
            test.title, title_found = m.group(1).strip(), True
            continue
        if m := _VOICES.match(line):
            for pair in re.split(r"[,;]", m.group(1)):
                if "=" in pair:
                    who, voice = (p.strip() for p in pair.split("=", 1))
                    test.voice_overrides[NARRATOR if who.lower() == "narrator" else who] = voice
            continue
        if _IGNORED_HEADERS.match(line):
            continue

        if m := _PAUSE.match(line):
            inner = m.group(1).strip()
            # "[Pause: you now have 30 seconds to look at questions 7 to 10.]" is
            # an announcement the narrator reads, followed by real silence.
            # "[Pause 5]" / "[Pause: 30 seconds]" is silence only.
            announced = len(inner.split()) >= 4
            # "...you have some time to look at questions 1 to 6" -> exam-like 20 s
            seconds = pause_seconds(inner, default=20.0 if announced else 5.0)
            if announced:
                announcement = inner[0].upper() + inner[1:]
                test.segments.append(Segment("speech", NARRATOR, announcement, line=number))
            test.segments.append(Segment("pause", seconds=seconds, text=inner, line=number))
            continue

        if line.startswith("[") and line.endswith("]"):
            test.warnings.append(f"Line {number}: skipped stage direction {line[:50]}")
            continue

        labelled = _speaker_line(line)
        if labelled:
            speaker, text = labelled
        elif last_speaker and not _NARRATOR_CUES.match(line):
            speaker, text = last_speaker, line
        else:
            speaker, text = NARRATOR, line

        if speaker != NARRATOR:
            last_speaker = speaker
            if speaker not in test.speakers:
                test.speakers.append(speaker)
        test.segments.append(Segment("speech", speaker, text, line=number))

    test.questions = "\n".join(question_lines).strip("\n")

    if not title_found:
        first = next((s.text for s in test.segments if s.kind == "speech"), "")
        if first:
            test.title = first if len(first) <= 60 else first[:57].rsplit(" ", 1)[0] + "..."
    if not any(s.kind == "speech" for s in test.segments):
        test.warnings.append("No spoken lines found. Paste a script with lines like 'Sam: Hello'.")
    if test.answers and not test.questions:
        test.warnings.append("Answer key found but no === QUESTIONS === section.")
    missing = [n for n in test.question_numbers if str(n) not in test.answers]
    if test.answers and missing:
        test.warnings.append(f"No answer given for question(s) {', '.join(map(str, missing))}.")
    return test

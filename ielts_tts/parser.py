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

from .grader import word_limit

NARRATOR = "Narrator"

# Question-set types used in @SET headers (official IELTS Listening task types).
SET_TYPES = {
    "form": "Form completion", "note": "Note completion", "table": "Table completion",
    "flowchart": "Flow-chart completion", "summary": "Summary completion",
    "sentence": "Sentence completion", "short": "Short-answer questions",
    "mcq": "Multiple choice", "mcq-multi": "Multiple choice (choose TWO/THREE)",
    "matching": "Matching", "map": "Plan / map / diagram labelling",
}
_SET_ALIASES = {
    "notes": "note", "flow-chart": "flowchart", "flow": "flowchart", "short-answer": "short",
    "multiple-choice": "mcq", "mcq2": "mcq-multi", "multi": "mcq-multi", "plan": "map",
    "diagram": "map", "labelling": "map", "label": "map", "sentences": "sentence",
}

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
# "@SET 11-14 | mcq | Choose the correct letter, A, B or C."
_SET = re.compile(r"^\s*@SET\s+(\d{1,2})\s*(?:[-–]\s*(\d{1,2}))?\s*\|\s*([\w -]+?)\s*(?:\|\s*(.*))?$", re.I)
_FENCE = re.compile(r"^\s*(?:```|~~~)")
_PART = re.compile(r"^\s*#{1,3}\s*PART\s+(\d)\b.*$", re.I | re.M)


@dataclass
class Segment:
    kind: str            # "speech" | "pause"
    speaker: str = ""
    text: str = ""
    seconds: float = 0.0
    line: int = 0        # 1-based line in the pasted script
    part: int = 0        # IELTS Part (1-4), 0 when unknown
    auto: bool = False   # inserted by the tool (standard narration), not written in the script


@dataclass
class Test:
    title: str = "Untitled test"
    segments: list = field(default_factory=list)
    speakers: list = field(default_factory=list)      # in order of appearance, Narrator excluded
    voice_overrides: dict = field(default_factory=dict)
    questions: str = ""
    answers: dict = field(default_factory=dict)       # "1" -> "Whitfield"
    answer_groups: list = field(default_factory=list) # [[21, 22]] for "choose TWO" questions
    sets: list = field(default_factory=list)          # @SET headers: start, end, type, rubric, limit
    parts: list = field(default_factory=list)         # per-Part view for multi-part tests
    kind: str = "custom"                              # part1..part4 | full | custom
    warnings: list = field(default_factory=list)

    @property
    def question_numbers(self):
        return numbers_in(self.questions, self.answers, self.sets)

    def to_dict(self):
        data = asdict(self)
        data["question_numbers"] = self.question_numbers
        data["has_narrator"] = any(s.speaker == NARRATOR for s in self.segments)
        return data


def numbers_in(questions: str, answers: dict, sets: list) -> list:
    """Question numbers from the paper (numbered lines and gaps), the key and @SET ranges."""
    paper = "\n".join(line for line in _strip_fences(questions).splitlines() if not _SET.match(line))
    nums = {int(m.group(1) or m.group(2)) for m in _QUESTION_NUM.finditer(paper)}
    nums |= {int(n) for n in answers}
    for s in sets:
        nums |= set(range(s["start"], s["end"] + 1))
    return sorted(nums)


def _strip_fences(text: str) -> str:
    """Drop ``` blocks (text maps, diagrams) so their contents aren't read as questions."""
    out, inside = [], False
    for line in text.splitlines():
        if _FENCE.match(line):
            inside = not inside
            continue
        if not inside:
            out.append(line)
    return "\n".join(out)


def parse_set(line: str):
    m = _SET.match(line)
    if not m:
        return None
    raw_type = m.group(3).strip().lower().replace(" ", "-")
    qtype = _SET_ALIASES.get(raw_type, raw_type)
    rubric = (m.group(4) or "").strip()
    start = int(m.group(1))
    return {"start": start, "end": int(m.group(2) or start), "type": qtype,
            "known": qtype in SET_TYPES, "rubric": rubric, "limit": word_limit(rubric)}


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
            if section == "questions":
                question_lines.append("")
            continue

        if _SECTION.match(line):
            section = "answers" if re.search(r"answer|key", line, re.I) else "questions"
            continue
        if section == "questions":
            question_lines.append(raw.rstrip())
            if (qset := parse_set(line)):
                test.sets.append(qset)
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

        if _PART.match(line):              # "### PART 2" is structure, not a title
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
    for group in test.answer_groups:      # "choose TWO" answers are letter sets
        for qset in test.sets:
            if qset["start"] <= group[0] <= qset["end"] and qset["type"] == "mcq":
                qset["type"] = "mcq-multi"

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


PART_RANGES = {1: (1, 10), 2: (11, 20), 3: (21, 30), 4: (31, 40)}


def _guess_part(test: Test) -> int:
    nums = test.question_numbers
    return (nums[0] - 1) // 10 + 1 if nums and 1 <= nums[0] <= 40 else 0


def _end_of_part(part: int, line: int) -> list:
    return [Segment("speech", NARRATOR, f"That is the end of Part {part}. "
                    "You now have half a minute to check your answers.", line=line, part=part, auto=True),
            Segment("pause", seconds=30.0, text="half a minute to check your answers",
                    line=line, part=part, auto=True)]


def unwrap(script: str) -> str:
    """Drop an outer ```text ... ``` fence copied along with Claude's answer."""
    lines = script.strip("\n").splitlines()
    if len(lines) >= 2 and lines[0].strip().startswith("```") and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1])
    return script


def parse_test(script: str, kind: str = "custom") -> Test:
    """Parse a script that may contain several Parts (### PART 1 ... ### PART 4).

    Each block is parsed with parse(); the result is one Test whose segments are
    tagged with their Part, plus a per-Part view in test.parts. Full tests get the
    standard between-Part narration added where the script leaves it out.
    """
    script = unwrap(script)
    markers = list(_PART.finditer(script))
    if not markers:
        test = parse(script)
        test.kind = kind
        part = int(kind[4:]) if kind.startswith("part") else _guess_part(test)
        for seg in test.segments:
            seg.part = part
        if part:
            test.parts = [{"n": part, "title": test.title, "questions": test.questions,
                           "numbers": test.question_numbers, "sets": test.sets}]
        return test

    preamble = parse(script[:markers[0].start()])
    combined = Test(kind="full" if len(markers) > 1 else kind)
    combined.voice_overrides.update(preamble.voice_overrides)
    has_title = bool(re.search(r"^\s*title\s*:", script[:markers[0].start()], re.I | re.M))
    titles = []

    for i, m in enumerate(markers):
        part = int(m.group(1))
        body_start = m.end()
        body_end = markers[i + 1].start() if i + 1 < len(markers) else len(script)
        offset = script.count("\n", 0, body_start)
        block = parse(script[body_start:body_end])
        for seg in block.segments:
            seg.part, seg.line = part, seg.line + offset
        segments = block.segments
        is_last = i == len(markers) - 1
        if combined.kind == "full" and not is_last:
            said_end = any(s.kind == "speech" and re.search(r"end of part", s.text, re.I)
                           for s in segments[-3:])
            ends_with_pause = bool(segments) and segments[-1].kind == "pause"
            if not said_end:
                segments = segments + _end_of_part(part, segments[-1].line if segments else offset)
            elif not ends_with_pause:
                segments = segments + _end_of_part(part, segments[-1].line)[1:]
        combined.segments.extend(segments)
        for who in block.speakers:
            if who not in combined.speakers:
                combined.speakers.append(who)
        combined.voice_overrides.update(block.voice_overrides)
        combined.answers.update(block.answers)
        combined.answer_groups.extend(block.answer_groups)
        combined.sets.extend(block.sets)
        combined.warnings.extend(f"Part {part}: {w}" for w in block.warnings)
        combined.parts.append({"n": part, "title": block.title, "questions": block.questions,
                               "numbers": block.question_numbers, "sets": block.sets})
        titles.append(block.title)

    combined.questions = "\n\n".join(p["questions"] for p in combined.parts if p["questions"])
    if has_title:
        combined.title = preamble.title
    elif len(markers) > 1:
        combined.title = "Full Listening Test"
    else:
        combined.title = titles[0]
    return combined


def detect_task(test: Test) -> str:
    """Which task page a parsed script belongs to: part1..part4, full or custom."""
    found = [p["n"] for p in test.parts]
    if found == [1, 2, 3, 4]:
        return "full"
    if len(found) == 1 and found[0] in PART_RANGES:
        return f"part{found[0]}"
    return "custom"

"""Build the copy-paste prompts that make Claude write exam-accurate scripts.

Each task page (Part 1-4, Full Test) asks for a topic, a question-type focus,
a difficulty and an accent mix; this module turns those into one prompt made of
the Part template (prompts/partN.md) + a concrete question plan + the shared
strict-format rules (prompts/_format.md).
"""

import json
import random
import re
from pathlib import Path

PROMPTS = Path(__file__).resolve().parent / "prompts"
TASKS = ("part1", "part2", "part3", "part4", "full")

# ---------------------------------------------------------------------------
# Official rubric wording, per question type
# ---------------------------------------------------------------------------
R = {
    "form": "Complete the form below. Write ONE WORD AND/OR A NUMBER for each answer.",
    "note1": "Complete the notes below. Write ONE WORD AND/OR A NUMBER for each answer.",
    "note": "Complete the notes below. Write ONE WORD ONLY for each answer.",
    "table1": "Complete the table below. Write ONE WORD AND/OR A NUMBER for each answer.",
    "table": "Complete the table below. Write NO MORE THAN TWO WORDS for each answer.",
    "mcq": "Choose the correct letter, A, B or C.",
    "mcq-multi": "Choose TWO letters, A–E.",
    "sentence": "Complete the sentences below. Write ONE WORD ONLY for each answer.",
    "summary": "Complete the summary below. Write ONE WORD ONLY for each answer.",
    "short": "Answer the questions below. Write NO MORE THAN TWO WORDS AND/OR A NUMBER for each answer.",
    "flowchart": "Complete the flow-chart below. Write ONE WORD ONLY for each answer.",
}
COUNT = {1: "ONE", 2: "TWO", 3: "THREE", 4: "FOUR", 5: "FIVE", 6: "SIX", 7: "SEVEN", 8: "EIGHT"}


def _letters(n_items: int, spare: int) -> str:
    return f"A–{chr(ord('A') + n_items + spare - 1)}"


def matching_rubric(a, b, spare=2):
    n = b - a + 1
    return (f"Choose {COUNT[n]} answers from the box and write the correct letter, "
            f"{_letters(n, spare)}, next to Questions {a}–{b}.")


def map_rubric(a, b, spare=3, kind="map"):
    return f"Label the {kind} below. Write the correct letter, {_letters(b - a + 1, spare)}, next to Questions {a}–{b}."


def flow_letters_rubric(a, b, spare=2):
    n = b - a + 1
    return (f"Complete the flow-chart below. Choose {COUNT[n]} answers from the box and write the correct "
            f"letter, {_letters(n, spare)}, next to Questions {a}–{b}.")


# How each set type should look on the question paper.
LAYOUT_HINTS = {
    "form": "a booking/registration form: a heading in CAPITALS, then 'Label: value' lines; include 2–3 lines "
            "already filled in (not questions) and put each gap as 'N ________' after its label",
    "note": "notes: a heading, 2–3 short sub-headings, and lines starting with '–'; each gap 'N ________' sits "
            "inside a short note so the gap's grammar shows what kind of word is needed",
    "table": "a table written as pipe-separated rows (header row first, 3 columns); gaps 'N ________' in cells, "
             "with some cells already filled in",
    "mcq": "each question as 'N. <stem>' followed by three options 'A  …', 'B  …', 'C  …' on separate lines",
    "mcq-multi": "a line 'Questions A and B' (the two numbers), a 'Which TWO …?' question, then five options "
                 "'A  …' to 'E  …'; ONE answer line for the pair, e.g. '21-22. B, D'",
    "matching": "a stem line ('What does the speaker say about each of the following …?' / 'Which comment do "
                "the students make about each …?'), the box of options as lines 'A  …', then the numbered "
                "items 'N. <item> ________'; options outnumber items by 2",
    "map": "a text map/plan between ~~~ lines with ★ (You are here), paths, 3–4 named landmarks and the lettered "
           "unlabelled places; then the numbered items 'N. <place> ________'; letters outnumber items by 3",
    "flowchart": "steps on separate lines with a line containing only '↓' between them; each gap 'N ________' "
                 "inside a step",
    "flowchart-letters": "the box of options as lines 'A  …' first, then the steps on separate lines with '↓' "
                         "lines between them and gaps 'N ________'",
    "sentence": "numbered sentences 'N. <sentence with a ________ gap>'",
    "summary": "a short summary paragraph (with a title line) containing the gaps 'N ________' in order",
    "short": "numbered questions 'N. <question>? ________'",
}


def S(a, b, qtype, rubric, hint=None):
    return {"start": a, "end": b, "type": qtype, "rubric": rubric, "hint": hint or LAYOUT_HINTS[qtype]}


# ---------------------------------------------------------------------------
# Question plans per Part. "mix" = layouts seen in recent real papers.
# split = last question of the first block (narrator break), None = no break (Part 4).
# ---------------------------------------------------------------------------
PLANS = {
    "part1": {
        "mix": [
            {"split": 6, "sets": [S(1, 6, "form", R["form"]), S(7, 10, "note", R["note1"])]},
            {"split": 5, "sets": [S(1, 5, "note", R["note1"]), S(6, 10, "note", R["note1"])]},
            {"split": 6, "sets": [S(1, 6, "table", R["table1"]), S(7, 10, "note", R["note1"])]},
            {"split": 7, "sets": [S(1, 7, "form", R["form"]), S(8, 10, "mcq", R["mcq"])]},
        ],
        "form": {"split": 6, "sets": [S(1, 6, "form", R["form"]), S(7, 10, "form", R["form"])]},
        "note": {"split": 5, "sets": [S(1, 5, "note", R["note1"]), S(6, 10, "note", R["note1"])]},
        "table": {"split": 5, "sets": [S(1, 5, "table", R["table1"]), S(6, 10, "table", R["table1"])]},
        "mcq": {"split": 5, "sets": [S(1, 5, "mcq", R["mcq"]), S(6, 10, "mcq", R["mcq"])]},
    },
    "part2": {
        "mix": [
            {"split": 14, "sets": [S(11, 14, "mcq", R["mcq"]), S(15, 20, "map", map_rubric(15, 20))]},
            {"split": 16, "sets": [S(11, 16, "matching", matching_rubric(11, 16)), S(17, 20, "mcq", R["mcq"])]},
            {"split": 14, "sets": [S(11, 12, "mcq-multi", R["mcq-multi"]), S(13, 14, "mcq-multi", R["mcq-multi"]),
                                   S(15, 20, "map", map_rubric(15, 20, kind="plan"))]},
            {"split": 15, "sets": [S(11, 15, "mcq", R["mcq"]), S(16, 20, "note", R["note"])]},
        ],
        "mcq": {"split": 15, "sets": [S(11, 15, "mcq", R["mcq"]), S(16, 20, "mcq", R["mcq"])]},
        "map": {"split": 15, "sets": [S(11, 15, "map", map_rubric(11, 15, kind="plan")),
                                      S(16, 20, "map", map_rubric(16, 20))]},
        "matching": {"split": 15, "sets": [S(11, 15, "matching", matching_rubric(11, 15)),
                                           S(16, 20, "matching", matching_rubric(16, 20))]},
        "mcq-multi": {"split": 14, "sets": [S(11, 12, "mcq-multi", R["mcq-multi"]), S(13, 14, "mcq-multi", R["mcq-multi"]),
                                            S(15, 16, "mcq-multi", R["mcq-multi"]), S(17, 18, "mcq-multi", R["mcq-multi"]),
                                            S(19, 20, "mcq-multi", R["mcq-multi"])]},
        "note": {"split": 15, "sets": [S(11, 15, "note", R["note"]), S(16, 20, "note", R["note"])]},
    },
    "part3": {
        "mix": [
            {"split": 25, "sets": [S(21, 25, "mcq", R["mcq"]), S(26, 30, "matching", matching_rubric(26, 30))]},
            {"split": 24, "sets": [S(21, 22, "mcq-multi", R["mcq-multi"]), S(23, 24, "mcq-multi", R["mcq-multi"]),
                                   S(25, 30, "matching", matching_rubric(25, 30))]},
            {"split": 25, "sets": [S(21, 25, "mcq", R["mcq"]),
                                   S(26, 30, "flowchart", flow_letters_rubric(26, 30), LAYOUT_HINTS["flowchart-letters"])]},
            {"split": 24, "sets": [S(21, 24, "sentence", R["sentence"]), S(25, 30, "mcq", R["mcq"])]},
        ],
        "mcq": {"split": 25, "sets": [S(21, 25, "mcq", R["mcq"]), S(26, 30, "mcq", R["mcq"])]},
        "mcq-multi": {"split": 24, "sets": [S(21, 22, "mcq-multi", R["mcq-multi"]), S(23, 24, "mcq-multi", R["mcq-multi"]),
                                            S(25, 26, "mcq-multi", R["mcq-multi"]), S(27, 28, "mcq-multi", R["mcq-multi"]),
                                            S(29, 30, "mcq-multi", R["mcq-multi"])]},
        "matching": {"split": 25, "sets": [S(21, 25, "matching", matching_rubric(21, 25)),
                                           S(26, 30, "matching", matching_rubric(26, 30))]},
        "flowchart": {"split": 25, "sets": [S(21, 25, "flowchart", R["flowchart"]),
                                            S(26, 30, "flowchart", flow_letters_rubric(26, 30),
                                              LAYOUT_HINTS["flowchart-letters"])]},
        "sentence": {"split": 25, "sets": [S(21, 25, "sentence", R["sentence"]), S(26, 30, "sentence", R["sentence"])]},
        "summary": {"split": 25, "sets": [S(21, 25, "summary", R["summary"]), S(26, 30, "summary", R["summary"])]},
    },
    "part4": {
        "mix": [
            {"split": None, "sets": [S(31, 40, "note", R["note"])]},
            {"split": None, "sets": [S(31, 40, "note", R["note"])]},
            {"split": None, "sets": [S(31, 40, "note", R["note"])]},
            {"split": None, "sets": [S(31, 36, "note", R["note"]), S(37, 40, "flowchart", R["flowchart"])]},
        ],
        "note": {"split": None, "sets": [S(31, 40, "note", R["note"])]},
        "summary": {"split": None, "sets": [S(31, 35, "note", R["note"]), S(36, 40, "summary", R["summary"])]},
        "sentence": {"split": None, "sets": [S(31, 40, "sentence", R["sentence"])]},
        "table": {"split": None, "sets": [S(31, 34, "note", R["note"]),
                                          S(35, 40, "table", "Complete the table below. Write ONE WORD ONLY for each answer.")]},
        "flowchart": {"split": None, "sets": [S(31, 35, "note", R["note"]), S(36, 40, "flowchart", R["flowchart"])]},
    },
}

FOCUS_LABELS = {
    "mix": "Real exam mix", "form": "Form completion", "note": "Note completion",
    "table": "Table completion", "mcq": "Multiple choice", "mcq-multi": "Choose TWO letters",
    "matching": "Matching", "map": "Map / plan labelling", "flowchart": "Flow-chart completion",
    "sentence": "Sentence completion", "summary": "Summary completion", "short": "Short-answer questions",
}
WORDS = {"part1": "650–850", "part2": "650–850", "part3": "700–900", "part4": "750–950"}
SPEAKERS = {"part3": ["two students and their tutor", "two students", "three students", "two students and their tutor"]}

DIFFICULTY = {
    "5.5-6.5": ("band 5.5–6.5 target", 3,
                "clear, moderately paced speech; answers stated fairly directly with light paraphrase; "
                "distractors noticeable if the learner listens carefully; everyday vocabulary."),
    "7-8": ("band 7–8 target, authentic Cambridge level", 4,
            "natural pace; consistent paraphrase between question paper and speech; distractors that require "
            "following the whole idea, not single words; some less common vocabulary in Parts 3–4."),
    "8.5-9": ("band 8.5–9 target, the hard end of the real test", 5,
              "fast natural delivery; heavy paraphrase; answers embedded in long sentences and lists; "
              "distractors that need inference; low-frequency academic vocabulary in Parts 3–4."),
}

DIFFICULTY_LABELS = {"5.5-6.5": "Band 5.5–6.5 (easier)", "7-8": "Band 7–8 (real exam)", "8.5-9": "Band 8.5–9 (hard)"}

BRITISH_VOICES = ("female British: bf_emma, bf_isabella, bf_alice, bf_lily; "
                  "male British: bm_fable, bm_lewis, bm_daniel (bm_george is reserved for the Narrator)")
AMERICAN_VOICES = "female American: af_heart, af_bella, af_nicole; male American: am_michael, am_adam, am_fenrir"


def topics() -> dict:
    return json.loads((PROMPTS / "topics.json").read_text(encoding="utf-8"))


def focus_options(task: str) -> list:
    if task == "full":
        return [{"id": "mix", "label": FOCUS_LABELS["mix"]}]
    return [{"id": f, "label": FOCUS_LABELS[f]} for f in PLANS[task]]


def random_topic(task: str, avoid=()) -> str:
    pool = topics()["part1" if task == "full" else task]
    fresh = [t for t in pool if t.lower() not in {a.lower() for a in avoid}]
    return random.choice(fresh or pool)


def choose_plan(task: str, focus: str = "mix", rng=random) -> dict:
    plans = PLANS[task]
    plan = plans.get(focus, plans["mix"])
    return rng.choice(plan) if isinstance(plan, list) else plan


def describe_plan(plan: dict) -> str:
    lines = []
    for s in plan["sets"]:
        rng = f"Questions {s['start']}–{s['end']}" if s["end"] > s["start"] else f"Question {s['start']}"
        lines.append(f"• {rng}: {FOCUS_LABELS.get(s['type'], s['type'])}.\n"
                     f"    Header: @SET {s['start']}-{s['end']} | {s['type']} | {s['rubric']}\n"
                     f"    Layout: {s['hint']}.")
    if plan["split"]:
        lines.append(f"• Block 1 = questions up to {plan['split']}; block 2 = questions {plan['split'] + 1} onwards "
                     f"(this is where the narrator's mid-part break goes).")
    return "\n".join(lines)


def summary(plan: dict) -> str:
    return " + ".join(f"{s['start']}–{s['end']} {FOCUS_LABELS.get(s['type'], s['type']).lower()}"
                      for s in plan["sets"])


def _voices(accent: str, task: str) -> str:
    where = ("on the line after the Title line at the very top (one line covering every speaker in all four Parts)"
             if task == "full" else "directly after the Title line")
    text = (f"Add a line `Voices: Narrator=bm_george, <Label>=<voice>, ...` {where}. Give every speaker a "
            f"voice of the right gender from: {BRITISH_VOICES}. ")
    if accent == "mixed":
        text += (f"Make ONE speaker{' per Part' if task == 'full' else ''} North American and give them one of: "
                 f"{AMERICAN_VOICES}. ")
    text += "Within a Part, never give two speakers the same voice."
    return text


def _layout(task: str, plan_numbers: str) -> str:
    if task == "full":
        return ("```text\nTitle: IELTS Listening Practice Test – <short name>\n"
                "Voices: Narrator=bm_george, <Label>=<voice>, ...\n"
                "### PART 1\nTitle: Part 1 – <short title>\n<narrator + dialogue lines>\n"
                "=== QUESTIONS ===\n<@SET headers and questions 1–10>\n=== ANSWERS ===\n<answers 1–10>\n"
                "### PART 2\n… same layout for questions 11–20 …\n"
                "### PART 3\n… same layout for questions 21–30 …\n"
                "### PART 4\n… same layout for questions 31–40 …\n```")
    n = task[-1]
    first_set = "@SET … | … | <exact rubric>"
    return (f"```text\n### PART {n}\nTitle: Part {n} – <short title>\n"
            f"Voices: Narrator=bm_george, <Label>=<voice>, ...\n"
            f"Narrator: Part {n}. You will hear …\n<all narrator lines, [Pause N] lines and speaker lines>\n"
            f"Narrator: That is the end of Part {n}.\n=== QUESTIONS ===\n{first_set}\n"
            f"<questions {plan_numbers}, each set starting with its @SET header>\n"
            f"=== ANSWERS ===\n<one line per question: number. answer>\n```")


def _fill(template: str, values: dict) -> str:
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def _part_section(task: str, topic: str, plan: dict, rng) -> str:
    """The 'WHAT A REAL PART N IS LIKE' + plan + structure section of one Part template."""
    text = (PROMPTS / f"{task}.md").read_text(encoding="utf-8")
    start = text.index("═══")
    end = text.index("VOICES:")
    body = text[start:end].strip()
    values = {"TOPIC": topic, "PLAN": describe_plan(plan), "WORDS": WORDS[task],
              "SPEAKERS": rng.choice(SPEAKERS.get(task, ["two students"]))}
    return f"TOPIC / SITUATION: {topic}\n\n" + _fill(body, values)


def build(task: str, topic: str = "", focus: str = "mix", difficulty: str = "7-8",
          accent: str = "british", seed=None) -> dict:
    """Return {"prompt", "plan", "topic"} for a task page."""
    if task not in TASKS:
        raise ValueError(f"unknown task {task}")
    rng = random.Random(seed)
    level, distractors, rules = DIFFICULTY.get(difficulty, DIFFICULTY["7-8"])
    accent_setting = (" (one speaker may be North American, using American vocabulary)"
                      if accent == "mixed" else "")
    shared = {"DISTRACTORS": str(distractors), "DIFFICULTY": level, "DIFFICULTY_RULES": rules,
              "ACCENT_SETTING": accent_setting, "VOICES": _voices(accent, task)}

    if task == "full":
        bank = topics()
        parts, plans = [], {}
        for n in range(1, 5):
            key = f"part{n}"
            part_topic = (topic if (topic and n == 1) else rng.choice(bank[key]))
            plan = choose_plan(key, "mix", rng)
            plans[key] = {"topic": part_topic, "summary": summary(plan)}
            section = _part_section(key, part_topic, plan, rng)
            # Full-test narration: half-minute checks after Parts 1–3, "Now turn to Part N" before Parts 2–4.
            if n < 4:
                section = section.replace(f"Narrator: That is the end of Part {n}.",
                                          f"Narrator: That is the end of Part {n}. You now have half a minute "
                                          f"to check your answers.\n[Pause 30]")
            else:
                section = section.replace("Narrator: That is the end of Part 4.",
                                          "Narrator: That is the end of Part 4.\n"
                                          "Narrator: That is the end of the Listening test.")
            if n > 1:
                section = section.replace(f"Narrator: Part {n}. You will hear",
                                          f"Narrator: Now turn to Part {n}.\nNarrator: Part {n}. You will hear")
            parts.append(f"█████ PART {n} (questions {n * 10 - 9}–{n * 10}) █████\n{section}")
        fmt = _fill((PROMPTS / "_format.md").read_text(encoding="utf-8"),
                    {**shared, "QUESTION_COUNT": "40", "NUMBERS": "1–40 (10 per Part)",
                     "LAYOUT": _layout("full", "")})
        prompt = _fill((PROMPTS / "full_test.md").read_text(encoding="utf-8"),
                       {**shared, "PARTS": "\n\n".join(parts), "TOTAL_WORDS": "2,900–3,500", "FORMAT": fmt})
        return {"prompt": _tidy(prompt), "plan": plans, "topic": "; ".join(p["topic"] for p in plans.values())}

    topic = topic.strip() or random_topic(task)
    plan = choose_plan(task, focus, rng)
    lo, hi = {"part1": (1, 10), "part2": (11, 20), "part3": (21, 30), "part4": (31, 40)}[task]
    fmt = _fill((PROMPTS / "_format.md").read_text(encoding="utf-8"),
                {**shared, "QUESTION_COUNT": "10", "NUMBERS": f"{lo}–{hi}", "LAYOUT": _layout(task, f"{lo}–{hi}")})
    template = (PROMPTS / f"{task}.md").read_text(encoding="utf-8")
    prompt = _fill(template, {**shared, "TOPIC": topic, "PLAN": describe_plan(plan), "WORDS": WORDS[task],
                              "SPEAKERS": rng.choice(SPEAKERS.get(task, ["two students"])), "FORMAT": fmt})
    return {"prompt": _tidy(prompt), "plan": {task: {"topic": topic, "summary": summary(plan)}}, "topic": topic}


def _tidy(text: str) -> str:
    leftover = re.findall(r"\{\{\w+\}\}", text)
    if leftover:
        raise ValueError(f"unfilled placeholders: {leftover}")
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"

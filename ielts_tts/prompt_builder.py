"""Build the copy-paste prompts that ask Claude for a practice test.

Claude decides the content (topic, speakers, question types, pattern, difficulty)
from its knowledge of real papers. The prompt only fixes the output format the app
needs to voice, display and mark the test (prompts/_format.md), plus an optional
note from the learner.
"""

import re
from pathlib import Path

PROMPTS = Path(__file__).resolve().parent / "prompts"
TASKS = ("part1", "part2", "part3", "part4", "full")
NUMBERS = {"part1": "1–10", "part2": "11–20", "part3": "21–30", "part4": "31–40",
           "full": "1–40 (1–10 in Part 1, 11–20 in Part 2, 21–30 in Part 3, 31–40 in Part 4)"}
MAX_NOTE = 600


def _read(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")


def build(task: str, note: str = "") -> dict:
    """Return {"prompt": text} for a task page; note is the learner's optional request."""
    if task not in TASKS:
        raise ValueError(f"unknown task {task}")
    note = re.sub(r"\s+", " ", note or "").strip()[:MAX_NOTE]
    note_block = (f"\nThe learner adds this request (follow it as long as the test stays realistic):\n"
                  f"\"{note}\"\n") if note else ""
    template = _read("full_test.md" if task == "full" else f"{task}.md")
    fmt = _read("_format.md").replace("{{NUMBERS}}", NUMBERS[task])
    prompt = template.replace("{{NOTE}}", note_block).replace("{{FORMAT}}", "\n" + fmt)
    leftover = re.findall(r"\{\{\w+\}\}", prompt)
    if leftover:
        raise ValueError(f"unfilled placeholders: {leftover}")
    return {"prompt": re.sub(r"\n{3,}", "\n\n", prompt).strip() + "\n"}

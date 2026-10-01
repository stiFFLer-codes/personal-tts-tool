"""Mark answers the way an IELTS examiner would (spelling counts, case doesn't).

Answer key syntax (one per line under === ANSWERS ===):
    1. Whitfield
    2. 23(rd) March | March 23(rd)       '|' or ' / ' = alternatives, (...) = optional
    7. waterproof jacket(s)
    21-22. B, D                          'choose TWO' - letters accepted in any order
"""

import itertools
import re

_NUMBERS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11",
    "twelve": "12", "thirteen": "13", "fourteen": "14", "fifteen": "15", "sixteen": "16",
    "seventeen": "17", "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30",
    "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70", "eighty": "80",
    "ninety": "90", "hundred": "100",
}

# Listening raw score (out of 40) -> band. Same table for Academic and General Training.
_BANDS = [(39, 9.0), (37, 8.5), (35, 8.0), (32, 7.5), (30, 7.0), (26, 6.5), (23, 6.0),
          (18, 5.5), (16, 5.0), (13, 4.5), (10, 4.0), (8, 3.5), (6, 3.0), (4, 2.5)]


def band(score: int, total: int = 40):
    if total != 40:
        return None
    return next((b for minimum, b in _BANDS if score >= minimum), 0.0 if score == 0 else 2.0)


def normalise(text: str) -> str:
    text = text.lower().replace("’", "'")
    text = re.sub(r"(\d),(\d{3})", r"\1\2", text)                 # 1,200 -> 1200
    text = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", text)           # 23rd -> 23
    text = re.sub(r"\b([ap])\.m\b\.?", r"\1m", text)                # a.m. -> am
    text = re.sub(r"(\d)(am|pm)\b", r"\1 \2", text)                  # 9am -> 9 am
    text = re.sub(r"[^\w\s']", " ", text.replace("-", " "))
    words = [_NUMBERS.get(w, w) for w in text.split()]
    while words and words[0] in ("a", "an", "the"):
        words = words[1:]
    return " ".join(words)


def _expand(option: str):
    """'waterproof (rain) jacket(s)' -> every combination with/without each (...) part."""
    parts = re.split(r"(\([^)]*\))", option)
    optional = [i for i, p in enumerate(parts) if p.startswith("(")]
    for keep in itertools.product([False, True], repeat=len(optional)):
        chosen = list(parts)
        for i, k in zip(optional, keep):
            chosen[i] = chosen[i][1:-1] if k else ""
        yield normalise("".join(chosen))


def accepted(key: str) -> set:
    options = re.split(r"\s*\|\s*|\s+/\s+|\s+OR\s+", key.strip())
    return {variant for option in options for variant in _expand(option) if variant}


def is_letter_set(key: str) -> bool:
    return bool(re.fullmatch(r"\s*[A-Ia-i](?:\s*(?:,|and|&|\s)\s*[A-Ia-i])+\s*", key))


def _letters(text: str) -> list:
    return [c.upper() for c in re.findall(r"\b[A-Ia-i]\b", text)]


def grade(answers: dict, user: dict, groups=None) -> dict:
    """answers/user: {"1": "..."}; groups: [[21, 22], ...] for 'choose TWO' questions."""
    results, grouped = {}, set()

    for group in groups or []:
        nums = [str(n) for n in group]
        key = set(_letters(answers.get(nums[0], "")))
        seen = set()
        for n in nums:
            letter = (_letters(user.get(n, "")) or [""])[0]
            ok = letter in key and letter not in seen
            seen.add(letter)
            results[n] = {"given": user.get(n, ""), "correct": ok, "key": answers.get(n, "")}
            grouped.add(n)

    for n, key in answers.items():
        if n in grouped:
            continue
        given = user.get(n, "")
        if is_letter_set(key):      # e.g. "B, D" on one line: all letters, any order
            ok = sorted(_letters(given)) == sorted(_letters(key))
        else:
            ok = normalise(given) in accepted(key) if given.strip() else False
        results[n] = {"given": given, "correct": ok, "key": key}

    ordered = dict(sorted(results.items(), key=lambda kv: int(kv[0])))
    score = sum(r["correct"] for r in ordered.values())
    return {"score": score, "total": len(ordered), "band": band(score, len(ordered)), "results": ordered}

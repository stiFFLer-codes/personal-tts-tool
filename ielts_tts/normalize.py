"""Turn script text into text the TTS engine reads the way an IELTS speaker would.

espeak (Kokoro's phonemizer) already handles ordinals, acronyms and postcodes
well. What it gets wrong are exactly the things IELTS loves to test:

* spelled names  ``W-H-I-T-F-I-E-L-D``  -> read as one mushed word
* phone numbers  ``0412 556 789``        -> "four hundred and twelve..."
* money          ``£42.50``              -> "pound forty two point five zero"
"""

import re

_DIGIT_WORDS = {
    "0": "oh", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
}

# Two or more single letters joined by hyphens: W-H-I-T-E, b-r-o-w-n.
_SPELLED = re.compile(r"(?<![\w-])(?:[A-Za-z]-){1,}[A-Za-z](?![\w-])")
# Digit groups that read like a phone/reference number: at least five digits in
# total, optionally split by single spaces or hyphens (0412 556 789, 01632-960001).
_DIGIT_RUN = re.compile(r"(?<![\w.,£$€])\d+(?:[ -]\d+)*(?![\w.,]\d)")
_MONEY = re.compile(r"([£$€])\s?(\d[\d,]*)(?:\.(\d{2}))?(?!\d)")
_TIME = re.compile(r"\b(\d{1,2}):(\d{2})\b")
_BRACKETED = re.compile(r"\s*\[[^\]]*\]\s*|\s*\((?:[^)]*\b(?:laugh|sigh|pause|noise|sound)\w*\b[^)]*)\)\s*", re.I)
_MARKDOWN = re.compile(r"[*_`#]+")

_CURRENCY = {"£": ("pound", "pounds", "pence"), "$": ("dollar", "dollars", "cents"),
             "€": ("euro", "euros", "cents")}


def has_spelling(text: str) -> bool:
    return bool(_SPELLED.search(text))


def _digits(match: re.Match) -> str:
    raw = match.group(0)
    if sum(c.isdigit() for c in raw) < 5 and not (raw.startswith("0") and len(raw) >= 3):
        return raw
    groups = re.split(r"[ -]", raw)
    return ", ".join(" ".join(_DIGIT_WORDS[d] for d in group) for group in groups)


def _money(match: re.Match) -> str:
    symbol, whole, cents = match.groups()
    one, many, small = _CURRENCY[symbol]
    amount = whole.replace(",", "")
    spoken = f"{whole} {one if amount == '1' else many}"
    if cents and cents != "00":
        spoken += f" {int(cents)}" if symbol == "£" else f" and {int(cents)} {small}"
    return spoken


def _time(match: re.Match) -> str:
    hour, minute = match.groups()
    if minute == "00":
        return f"{int(hour)} o'clock"
    if minute.startswith("0"):
        return f"{int(hour)} oh {int(minute)}"
    return f"{int(hour)} {minute}"


def _clean(text: str) -> str:
    text = _BRACKETED.sub(" ", text)
    return _MARKDOWN.sub("", text)


def _say(text: str) -> str:
    text = _MONEY.sub(_money, text)
    text = _TIME.sub(_time, text)
    text = _DIGIT_RUN.sub(_digits, text)
    return re.sub(r"\s+", " ", text).strip()


def speech_parts(text: str) -> list:
    """Split a line into ("text", str) and ("letters", [..]) parts.

    Spelled words are returned as separate letters so the engine can say each one
    clearly with a real gap, like an IELTS speaker spelling a surname.
    """
    text, parts, last = _clean(text), [], 0
    for m in _SPELLED.finditer(text):
        before = _say(text[last:m.start()])
        if re.search(r"[A-Za-z0-9]", before):
            parts.append(("text", before))
        parts.append(("letters", [letter.upper() for letter in m.group(0).split("-")]))
        last = m.end()
    rest = _say(text[last:])
    if re.search(r"[A-Za-z0-9]", rest):
        parts.append(("text", rest))
    return parts


def for_speech(text: str) -> str:
    """The whole line as the engine will say it (letters shown comma-separated)."""
    return " ".join(value if kind == "text" else ", ".join(value) + "."
                    for kind, value in speech_parts(text))

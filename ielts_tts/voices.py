"""Voice catalogue and automatic casting of speakers to voices."""

import re

from .parser import NARRATOR

ACCENTS = {"a": "American", "b": "British"}
LANGS = {"a": "en-us", "b": "en-gb"}

# Best-sounding first (per Kokoro's own voice grades). British first, since
# most IELTS recordings use British speakers; American adds accent variety.
FEMALE_ORDER = ["bf_emma", "bf_isabella", "bf_alice", "bf_lily",
                "af_heart", "af_bella", "af_nicole", "af_sarah", "af_aoede", "af_kore"]
MALE_ORDER = ["bm_fable", "bm_lewis", "bm_daniel", "bm_george",
              "am_michael", "am_fenrir", "am_puck", "am_adam", "am_echo", "am_liam"]
DEFAULT_NARRATOR = "bm_george"

# Just enough to cast common IELTS names sensibly. Anything else is balanced.
_FEMALE = set("""
woman girl lady female mother mum mom wife daughter sister aunt receptionist
mrs ms miss madam clara sarah emma anna hannah sophie lucy kate katie jane mary
susan linda karen lisa julia laura rachel rebecca jessica jennifer amy emily
olivia chloe grace alice lily isabella mia ella zoe ruth helen maria sofia
nina eva elena fiona heather joanna jo louise megan natalie paula rose sally
tina wendy yuki priya ananya aisha fatima mei lin carol diana claire jenny
""".split())
_MALE = set("""
man boy gentleman male father dad husband son brother uncle mr sir
john james david michael robert william richard thomas mark paul peter steve
steven andrew daniel matthew tom tim jack harry oliver george charlie ben
adam simon nick nicholas tony greg gary kevin brian ian colin graham keith
martin neil philip stuart lewis luke ryan sean henry edward frank joe raj
rahul arjun ali omar hiroshi kenji carlos marco hans jake josh dan mike
""".split())


def guess_gender(name: str):
    """'f', 'm' or None. Looks at titles and first names: 'Mrs Lee', 'Man', 'Clara'."""
    for word in re.findall(r"[a-z]+", name.lower()):
        if word in _FEMALE:
            return "f"
        if word in _MALE:
            return "m"
    return None


def describe(voice_id: str) -> dict:
    accent, gender = voice_id[0], voice_id[1]
    name = voice_id.split("_", 1)[1].capitalize()
    return {
        "id": voice_id,
        "name": name,
        "accent": ACCENTS.get(accent, "Other"),
        "gender": "female" if gender == "f" else "male",
        "lang": LANGS.get(accent, "en-gb"),
        "label": f"{name} ({ACCENTS.get(accent, '?')} {'F' if gender == 'f' else 'M'})",
    }


def lang_for(voice_id: str) -> str:
    return LANGS.get(voice_id[:1], "en-gb")


def english_voices(all_voices) -> list:
    """Kokoro ships many languages; IELTS only needs British and American English."""
    ids = [v for v in all_voices if v[:1] in ACCENTS and v[1:2] in ("f", "m")]
    rank = {v: i for i, v in enumerate(FEMALE_ORDER + MALE_ORDER + [DEFAULT_NARRATOR])}
    return [describe(v) for v in sorted(ids, key=lambda v: (v[0] != "b", rank.get(v, 99), v))]


def assign(speakers, available, overrides=None, narrator=None) -> dict:
    """Give every speaker a distinct voice. Returns {speaker: voice_id} incl. Narrator."""
    overrides = {k: v for k, v in (overrides or {}).items() if v in available}
    cast = {}
    narrator_voice = narrator or overrides.get(NARRATOR) or DEFAULT_NARRATOR
    if narrator_voice not in available:
        narrator_voice = next(iter(available))
    cast[NARRATOR] = narrator_voice
    used = set(cast.values()) | set(overrides.values())

    def take(order, gender):
        for v in order:
            if v in available and v not in used:
                return v
        spare = [v for v in available if v[1] == gender and v not in used]
        return spare[0] if spare else next(v for v in order if v in available)

    counts = {"f": 0, "m": 0}
    known = {s: guess_gender(s) for s in speakers}
    for s, g in known.items():
        if g:
            counts[g] += 1

    for speaker in speakers:
        if speaker in overrides:
            cast[speaker] = overrides[speaker]
            continue
        gender = known[speaker]
        if gender is None:          # balance the cast: an unknown 'Sam' opposite 'Clara' is male
            gender = "m" if counts["m"] <= counts["f"] else "f"
            counts[gender] += 1
        voice = take(FEMALE_ORDER if gender == "f" else MALE_ORDER, gender)
        cast[speaker] = voice
        used.add(voice)
    return cast

# 🎧 IELTS Listening Studio

A personal, **offline** text-to-speech tool built for one job: **mastering the IELTS Listening section.**

Paste a listening script (from Claude, a book, anywhere). The studio gives every speaker a natural British
(or American) neural voice, adds the real exam pauses, and turns it into a test you can **practise** line by line
or **sit under exam conditions**, then marks your answers.

No cloud, no API keys, no subscriptions. After a one-time setup everything runs on your laptop.

**Claude writes the script → you paste it → the studio speaks it → you answer → it marks you.**

---

## Quick start (Windows)

1. Install **Python 3.12** from [python.org](https://www.python.org/downloads/) and tick **"Add python.exe to PATH"**.
2. Double-click **`setup.bat`** (one time: installs the voice engine and downloads the ~350 MB voice model).
3. Double-click **`run.bat`**. The studio opens in your browser at `http://127.0.0.1:8765`.

A sample test (*Part 1: Harbourview Bike Tours*) is already in the library. Pick it from **📚 Library**, hit
**Generate**, then take it in the **Exam** tab.

<details>
<summary>macOS / Linux</summary>

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m ielts_tts.download_models
python -m ielts_tts
```
</details>

## Daily workflow

1. **Get a script.** Open [`docs/CLAUDE_SCRIPT_PROMPT.md`](docs/CLAUDE_SCRIPT_PROMPT.md), copy the prompt into Claude,
   choose the part, topic and difficulty. Claude returns a script with questions and an answer key in the right format.
2. **Studio:** paste it and check the cast (change any voice and press ▶ to preview), then **Generate audio**.
   Save it to the library if you want to keep it.
3. **Exam:** the recording plays **once**, with no pause and no rewind, just like test day. Type answers as you listen.
   You get 2 minutes to check, then it's marked. Full 40-question tests show an **estimated band**.
4. **Practice:** review what you missed. Click any transcript line to jump there, loop a tricky line, slow it down to 0.9×,
   or turn on **Blind mode** to listen without the text.
5. **Progress:** every exam score is saved, so you can watch the trend go up. 📈

## What makes it IELTS-specific

| Feature | Why it matters |
|---|---|
| Distinct voice per speaker, auto-cast by name (Clara → female, Sam → male) | Part 1/3 conversations sound like real people |
| Separate **Narrator** voice for "You will hear…" and question breaks | Same structure as the real recording |
| `[Pause: you now have 30 seconds…]` → narrator reads it + **real 30 s silence** | Practise using reading time |
| Spelled names (`W-H-I-T-F-I-E-L-D`) said letter by letter with clear gaps | Spelling questions are a Part 1 staple |
| Phone numbers read digit by digit ("oh four one two…"), prices read naturally | Number traps |
| Exam mode: plays once, can't pause, 2-minute check time | Builds real test stamina |
| Marking with alternatives, optional words, numbers as digits or words, "choose TWO" in any order | Marked like the real answer key; spelling must be exact |
| Practice: line replay, loop, 0.75–1.25× speed, blind mode, keyboard shortcuts | Train weak spots fast |
| Export **WAV** (or **MP3** if `ffmpeg` is installed) | Listen on your phone while commuting |

**Keyboard (Practice):** `Space` play/pause · `←`/`→` previous/next line · `R` replay line · `L` loop · `B` blind mode

## Script format

Your script can be pasted as-is. Lines like `Name: text` are speakers; anything else is the narrator.
Full spec and examples are in [`docs/CLAUDE_SCRIPT_PROMPT.md`](docs/CLAUDE_SCRIPT_PROMPT.md).

```text
Title: Part 1 – Harbourview Bike Tours
You will hear a woman phoning a bike tour company to book a tour.
Sam: Good morning, Harbourview Bike Tours, Sam speaking.
Clara: It's W-H-I-T-F-I-E-L-D.
[Pause: you now have 30 seconds to look at questions 7 to 10.]

=== QUESTIONS ===
Name: Clara 1 ________

=== ANSWERS ===
1. Whitfield
```

## How it works

- **Voice engine:** [Kokoro](https://github.com/thewh1teagle/kokoro-onnx), an open-source 82M-parameter neural TTS model
  running locally on ONNX Runtime. That's the **only** dependency. The UI and server are plain Python standard library
  plus vanilla HTML/JS, so nothing loads from the internet.
- Each line is synthesised once and **cached**, so changing one speaker's voice only re-renders that speaker.
- Rendering runs at roughly 2× faster than real time on a typical laptop CPU (a 4-minute Part 1 takes 1–2 minutes the first time).

```
ielts_tts/
  parser.py       script → speakers, pauses, questions, answer key
  normalize.py    spelling / phone numbers / money → speakable text
  voices.py       voice catalogue + automatic casting
  engine.py       Kokoro synthesis, cache, WAV/MP3, timeline
  grader.py       IELTS-style marking + band table
  server.py       local web server (127.0.0.1 only)
  static/         the web UI
library/          your saved scripts (.txt)
output/ cache/ results/ models/   generated locally, git-ignored
```

Run the tests with `python -m unittest discover tests`.

## Honest limitations

- Kokoro has **British and American** English voices only. There's no Australian or NZ accent yet, and those do appear in IELTS.
  Mixing British and American speakers still trains you for accent variety.
- These are synthetic voices: very natural, but cleaner than a real recording (no background noise, no overlapping speech).
  Use official Cambridge IELTS books for a few full mocks closer to test day.
- `setup.bat` needs internet once (pip + model download). After that it's fully offline.

## Troubleshooting

- **"Voice model missing"**: run `setup.bat` again (it resumes and skips what's already downloaded).
- **Low disk space?** `python -m ielts_tts.download_models --small` gets a 92 MB model. It's smaller but often *slower* on CPUs.
- **Port busy**: the studio is already open in another window, or use `run.bat --port 8766`.
- **Python 3.14** isn't supported by the voice engine yet. Install 3.12 alongside it and `setup.bat` will pick it.

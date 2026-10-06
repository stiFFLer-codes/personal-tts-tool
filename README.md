# 🎧 Listening Studio

A personal, **offline** text-to-speech tool built for one job: **mastering the IELTS Listening section,
one Part at a time.**

The app has a page for each Part of the real test (Part 1 conversation, Part 2 monologue, Part 3 discussion,
Part 4 lecture) and one for a **Full Test**. Each page gives you a prompt to paste into Claude. **Claude decides
the content** (topic, speakers, question types, pattern, difficulty) from its knowledge of real past papers; the
prompt only fixes the format the app needs. You paste the reply back, the app checks the format, and then voices it with natural British (or American) neural voices and the real exam pauses. You sit it
**under exam conditions**, it marks you like an examiner, and Progress shows which question types cost you marks.

No cloud, no API keys, no subscriptions. After a one-time setup everything runs on your laptop.

**Pick a Part → copy the prompt → Claude writes the test → paste it back → listen once → get marked → drill your weak spots.**

---

## Quick start (Windows)

1. Install **Python 3.12** from [python.org](https://www.python.org/downloads/) and tick **"Add python.exe to PATH"**.
2. Double-click **`setup.bat`** (one time: installs the voice engine and downloads the ~350 MB voice model).
3. Double-click **`run.bat`**. The studio opens in your browser at `http://127.0.0.1:8765`.

Sample tests for every Part, plus two full 40-question tests, are already in the library. Open a Part page,
pick one from **📚 Library**, hit **Generate**, then **📝 Take as exam**.

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

1. **Pick a task** in the sidebar: Part 1, 2, 3, 4 or Full Test. Each page starts with a short guide to that Part:
   context, speakers, question types, traps and strategy.
2. **① Get a script:** there's one prompt per page. Optionally type a **Note to Claude** ("make it hard",
   "more map questions", "a lecture about marine biology"), click **Copy prompt**, then paste it into Claude
   ([Open Claude ↗](https://claude.ai/new)). Claude picks everything else, like a real paper would.
3. **② Paste Claude's reply** into the page. The **format checklist** confirms the app can voice and mark it: the right
   question numbers, a known type and instructions for every set, a complete answer key within the word limits, and
   no exam name in the text. If something fails, **Copy fix request** gives Claude the exact list.
4. **③ Generate & sit it:** check the cast (▶ previews a voice), generate the audio, then **📝 Take as exam**: it plays
   **once**, with no pause and no rewind. Full tests have the real 30-second checks between Parts and a Part navigator
   that follows the audio. You get 2 minutes at the end to check (computer-delivered timing), then it's marked.
   40-question tests show an **estimated band**.
5. **🎧 Practice:** review what you missed. Click anywhere on the **waveform** to jump (the silences and Part
   boundaries are visible), jump to any line, loop a tricky line, slow down to 0.9×, or use **Blind mode**.
6. **📈 Progress:** accuracy per Part and **per question type**, weakest first, with a **Drill this** button that opens
   the right Part with a note asking Claude for plenty of that question type.

Prompt files, the format spec and how to edit them: [`docs/CLAUDE_SCRIPT_PROMPT.md`](docs/CLAUDE_SCRIPT_PROMPT.md).
Have a script from a book or elsewhere? Use **Custom script** (link on Home); its checks are advice only.

## What makes it exam-specific

| Feature | Why it matters |
|---|---|
| Distinct voice per speaker, auto-cast by name (Clara → female, Sam → male) | Part 1/3 conversations sound like real people |
| Separate **Narrator** voice for "You will hear…" and question breaks | Same structure as the real recording |
| Narrator lines and `[Pause 30]` reading time exactly like the real recording; no mid-lecture break in Part 4 | Practise using reading time |
| Spelled names (`W-H-I-T-F-I-E-L-D`) said letter by letter with clear gaps | Spelling questions are a Part 1 staple |
| Phone numbers read digit by digit ("oh four one two…"), prices read naturally | Number traps |
| Exam mode: plays once, can't pause, 30 s checks between Parts, 2-minute check time | Builds real test stamina |
| Word limits enforced from the rubric ("ONE WORD ONLY" → two words = wrong) | Exactly how the real test is marked |
| Per-question-type analytics with "Drill this" | Spend time where marks are lost |
| Marking with alternatives, optional words, numbers as digits or words, "choose TWO" in any order | Marked like the real answer key; spelling must be exact |
| Practice: line replay, loop, 0.75–1.25× speed, blind mode, keyboard shortcuts | Train weak spots fast |
| Export **WAV** (or **MP3** if `ffmpeg` is installed) | Listen on your phone while commuting |
| "On air" studio look: live VU meter, ON AIR lamp, waveform seek bar, dark / light / auto theme | Easy on the eyes for long sessions |

**Keyboard (Practice):** `Space` play/pause · `←`/`→` previous/next line · `R` replay line · `L` loop · `B` blind mode

## Script format

Claude's reply is one code block in this format. Full spec in [`docs/CLAUDE_SCRIPT_PROMPT.md`](docs/CLAUDE_SCRIPT_PROMPT.md).

```text
### PART 1
Title: Part 1 – Harbourview Bike Tours
Voices: Narrator=bm_george, Sam=bm_fable, Clara=bf_emma
Narrator: Part 1. You will hear a woman phoning a bike tour company to book a tour.
Narrator: First, you have some time to look at questions 1 to 6.
[Pause 30]
Sam: Good morning, Harbourview Bike Tours, Sam speaking.
Clara: It's W-H-I-T-F-I-E-L-D.
=== QUESTIONS ===
@SET 1-6 | form | Complete the form below. Write ONE WORD AND/OR A NUMBER for each answer.
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
  parser.py       script → Parts, speakers, pauses, question sets, answer key
  validator.py    format checklist (numbering, sets, answer key, word limits)
  prompt_builder.py + prompts/   the Claude prompt per task + the shared output format
  normalize.py    spelling / phone numbers / money → speakable text
  voices.py       voice catalogue + automatic casting
  engine.py       Kokoro synthesis, cache, WAV/MP3, timeline per Part, waveform peaks
  grader.py       IELTS-style marking, word limits, band table, per-type tallies
  server.py       local web server (127.0.0.1 only)
  static/         the web UI (+ bundled fonts: Fraunces, Figtree, JetBrains Mono, OFL)
library/          sample tests (Parts 1–4, two full tests) + your saved scripts
output/ cache/ results/ models/   generated locally, git-ignored
```

Run the tests with `python -m unittest discover tests`.

## Honest limitations

- Kokoro has **British and American** English voices only. There's no Australian or NZ accent yet, and those do appear in IELTS.
  Mixing British and American speakers still trains you for accent variety.
- These are synthetic voices: very natural, but cleaner than a real recording (no background noise, no overlapping speech).
  Use official Cambridge IELTS books for a few full mocks closer to test day.
- The scripts are written by Claude, not taken from real papers. Claude models them on real papers and the checklist
  keeps the format right, but quality can vary, so read the transcript when an answer feels unfair.
- Map/plan labelling uses a text map in the question paper instead of a drawing.
- `setup.bat` needs internet once (pip + model download). After that the app is fully offline. Generating new scripts
  uses Claude, which is online.

## Troubleshooting

- **"Voice model missing"**: run `setup.bat` again (it resumes and skips what's already downloaded).
- **Low disk space?** `python -m ielts_tts.download_models --small` gets a 92 MB model. It's smaller but often *slower* on CPUs.
- **Port busy**: the studio is already open in another window, or use `run.bat --port 8766`.
- **Python 3.14** isn't supported by the voice engine yet. Install 3.12 alongside it and `setup.bat` will pick it.

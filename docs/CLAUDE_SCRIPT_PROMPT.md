# Getting exam-accurate scripts from Claude

**You don't need to copy anything from this file.** Every task page in the app (Part 1, Part 2, Part 3,
Part 4, Full Test) has one ready-made prompt: optionally type a **Note to Claude**, click **Copy prompt**,
paste it into Claude, and paste Claude's reply back into the page.

## Who decides what

- **Claude decides the content:** topic, setting, speakers, question types and how they're mixed, the
  instructions, where the narrator speaks and pauses, distractors and difficulty. The prompt asks it to base
  these on real past papers and recent tests, and to vary them instead of following a fixed template.
- **The prompt fixes only the format** the app needs to voice the script, show the question paper and mark
  the answers (see below), plus one rule: the exam's name must not appear anywhere in the output.
- **Your note** (optional, up to 600 characters) is added to the prompt as a request Claude follows as long as
  the test stays realistic. **Drill this** on the Progress page fills it in for you.

## Where the prompts live

| File | What it is |
|---|---|
| `ielts_tts/prompts/part1.md` … `part4.md` | A short brief: write one original Part n, indistinguishable from a real one |
| `ielts_tts/prompts/full_test.md` | The same for all four Parts in the real order, with the narration and checks between them |
| `ielts_tts/prompts/_format.md` | What's up to Claude, the strict output format and a format self-check |
| `ielts_tts/prompt_builder.py` | Joins brief + note + format and fills in the question numbers |

Edit the `.md` files to change the wording; the app picks up the changes on the next prompt.

## What the app adds by itself

- In a full test, if a Part doesn't end with "That is the end of Part n" and a pause, the app adds them (30 s check).
- A checking pause at the very end of the script is dropped: the app gives you 2 minutes to check after the
  recording stops, like the computer-delivered test.

## The strict script format

```text
### PART 2
Title: Part 2 – Brackenmoor Visitor Centre
Voices: Narrator=bm_george, Ranger=bf_isabella
Narrator: Part 2. You will hear a park ranger welcoming visitors to a national park visitor centre.
Narrator: First, you have some time to look at questions 11 to 14.
[Pause 30]
Narrator: Now listen carefully and answer questions 11 to 14.
Ranger: Good morning, everyone, and welcome…
Narrator: Before you hear the rest of the talk, you have some time to look at questions 15 to 20.
[Pause 30]
Narrator: Now listen and answer questions 15 to 20.
Ranger: …
Narrator: That is the end of Part 2.
=== QUESTIONS ===
@SET 11-14 | mcq | Choose the correct letter, A, B or C.
11. What change at the visitor centre does the ranger mention?
A  The café is serving food again.
B  Visitors no longer have to pay to park.
C  The building now stays open later.
@SET 15-20 | map | Label the map below. Write the correct letter, A–I, next to Questions 15–20.
~~~
   (text map with ★ You are here, landmarks and letters A–I)
~~~
15. Cycle hire ________
=== ANSWERS ===
11. B
15. D
```

| You write | The tool does |
|---|---|
| `### PART n` | Starts a Part (a full test has four). Optional on single-Part pages |
| `Title:` / `Voices:` | Test name; voice per speaker (`bm_george` = narrator) |
| `Narrator: …` / `Name: …` | Narrator voice / that speaker's voice |
| a line with no label | Continues the previous speaker (or the narrator at the start) |
| `[Pause 30]` | 30 seconds of real silence |
| `[Pause: you now have 30 seconds …]` | Older style: narrator reads it, then silence |
| `W-H-I-T-F-I-E-L-D` | Spelled clearly, letter by letter |
| `0412 556 789`, `CB2 4RT` | Read digit by digit / character by character |
| `@SET a-b \| type \| rubric` | Question set header. Types: `form, note, table, flowchart, summary, sentence, short, mcq, mcq-multi, matching, map`. The rubric's word limit is enforced when marking |
| `N ________` | Answer box for question N |
| `N. stem` + `A  option` lines | Multiple choice |
| `Day \| Place \| 3 ________` | Table row |
| `↓` on its own line | Flow-chart arrow |
| `~~~` … `~~~` | Map / plan drawn in monospace |
| `=== ANSWERS ===` | `2. 23(rd) \| twenty-third`: `\|` = alternatives, `( )` = optional; `21-22. B, D` = choose TWO, either order |

Claude replies with everything inside one ```` ```text ```` code block. Use Claude's copy button on the
block; if you paste the fence lines too, the app ignores them.

## If Claude's script fails a check

The checklist on the task page names the problem, for example *"Part 4 Q31–40: answer key breaks the word
limit: Q33 'coral polyps'"*. Either fix it in the paste box, or reply to Claude:

> Your script fails these format checks: <paste the ❌ lines>. Fix them and send the whole corrected code block again.

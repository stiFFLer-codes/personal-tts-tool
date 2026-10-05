# Getting exam-accurate scripts from Claude

**You don't need to copy anything from this file.** Every task page in the app (Part 1, Part 2, Part 3,
Part 4, Full Test) builds the right prompt for you: pick a topic, question types and difficulty, then
click **📋 Copy prompt**, paste it into Claude, and paste Claude's reply back into the page.

This file explains what those prompts contain and the strict script format they make Claude follow,
so you can tweak them or write scripts by hand.

## Where the prompts live

| File | What it is |
|---|---|
| `ielts_tts/prompts/part1.md` … `part4.md` | What each real Part is like (context, speakers, length, traps) and its exact narrator lines |
| `ielts_tts/prompts/full_test.md` | The whole 40-question test: difficulty curve and the narration that links the Parts |
| `ielts_tts/prompts/_format.md` | Shared quality rules, the strict output format and Claude's self-check list |
| `ielts_tts/prompts/topics.json` | About 30 realistic topics per Part, used by 🎲 |
| `ielts_tts/prompt_builder.py` | The question plans per Part (real-exam mixes and single-type drills) with the official rubric wording |

Edit the `.md` files to change the wording; the app picks up the changes on the next prompt. You can also
add your own topics to `topics.json`.

## What the real test looks like (and what the prompts enforce)

| Part | Context | Speakers | Usual question types | Narration |
|---|---|---|---|---|
| 1 | Everyday social (booking, enquiry) | 2 | Form / note / table completion, sometimes MCQ | Reading time → first block → "Before you hear the rest…" → second block |
| 2 | Everyday social monologue (guide, presenter) | 1 | MCQ + map/plan labelling or matching, choose TWO | Same two-block pattern |
| 3 | Educational discussion (students + tutor) | 2–4 | MCQ, matching, choose TWO, flow-chart, sentence completion | Same two-block pattern |
| 4 | Academic lecture | 1 | Note completion, ONE WORD ONLY (sometimes summary/flow-chart) | **No break in the middle** |

- 40 questions, about 30 minutes, heard **once**, answers in the order you hear them.
- On the computer-delivered test there's a 30-second check after each of Parts 1–3 and 2 minutes at the end.
- Word limits come from the instructions ("ONE WORD ONLY", "ONE WORD AND/OR A NUMBER", "NO MORE THAN TWO WORDS"). Going over is wrong, and so is misspelling.
- The Part 1 example was removed from the real test in 2020, so the prompts don't include one.

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

> Your script fails these checks: <paste the ❌ lines>. Fix them and send the whole corrected code block again.

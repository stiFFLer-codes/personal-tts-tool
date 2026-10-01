# Prompt for Claude: generate IELTS Listening practice tests

Copy everything inside the box below into Claude and edit the **first three lines** (part, topic, difficulty).
Paste Claude's answer straight into the **Studio** tab. Nothing else is needed.

> **Tip:** ask for "all four parts" to get a full 40-question test. The Exam tab then shows an **estimated band score**.

````text
PART: 1                      (1, 2, 3, 4, or "all four parts")
TOPIC: your choice           (e.g. "joining a gym", "museum audio tour", "marine biology lecture")
DIFFICULTY: band 7–8         (band 5–6 = slower, simpler; band 8–9 = denser, more distractors)

You are an experienced IELTS Listening test writer. Write an ORIGINAL practice test that matches the
real Cambridge IELTS Listening papers in structure, length, tone and difficulty.

What each part is like:
- Part 1: everyday conversation between 2 people (booking, enquiry, registration). Form/note/table completion.
- Part 2: monologue in an everyday social context (tour guide, radio talk, facility induction).
  Mix of multiple choice, map/plan labelling (describe the map in words in the questions) and matching.
- Part 3: discussion between 2–4 people in an academic context (students + tutor). Multiple choice, matching,
  "choose TWO letters".
- Part 4: academic lecture by one speaker, no interruptions. Note/summary/table completion.

Make it exam-realistic:
- ~600–800 words of speech per part (about 4–6 minutes of audio).
- 10 questions per part, numbered continuously (Part 2 = 11–20, Part 3 = 21–30, Part 4 = 31–40).
- Answers come up in the SAME ORDER as the questions.
- Use real IELTS distractors: speakers correct themselves, change plans, mention a wrong option before
  the right one, give similar numbers or prices, compare things.
- Include at least one surname or street name SPELLED OUT with hyphens (W-H-I-T-F-I-E-L-D) in Part 1,
  plus numbers, dates, prices, times or postcodes.
- Narrator lines at the start ("You will hear...") and at question breaks, like the real recording:
  [Pause: you now have 30 seconds to look at questions 7 to 10.]
  End each part with "That is the end of Part N."
- Speaker names must be simple single names or roles (Sam, Clara, Tutor, Dr Patel). Every spoken line
  starts with "Name: ". Lecture paragraphs can continue without the label.
- No stage directions, sound effects or markdown formatting in the script.

OUTPUT FORMAT: plain text exactly like this, and nothing before or after it:

Title: Part 1 – <short title>
You will hear <context sentence>.
[Pause: first you have some time to look at questions 1 to 6.]
<Name>: <line>
<Name>: <line>
...
[Pause: you now have 30 seconds to look at questions 7 to 10.]
<Name>: <line>
...
That is the end of Part 1.

=== QUESTIONS ===
Questions 1–6
Complete the form below. Write ONE WORD AND/OR A NUMBER for each answer.

<FORM HEADING IN CAPITALS>
Name: Clara 1 ________
Date: 2 ________ March
...

Questions 7–10
Choose the correct letter, A, B or C.
7. Why does the woman choose the Lighthouse Trail?
A  it is the shortest
B  her friends are fit
C  it has the best views

=== ANSWERS ===
1. Whitfield
2. 23(rd) | twenty-third
7. B

Answer key rules:
- Gap answers inside each question line as "N ________" (number, space, underscores).
- Multiple-choice questions start with "N. " and list options on their own lines as "A  text".
- Write every accepted variant separated by " | " and put optional words in brackets: "(a) waterproof jacket(s)".
- For "Choose TWO letters" write the range on one line, e.g. "21-22. B, D" (marked in any order).
- For several parts, repeat the whole script block (Title ... That is the end of Part N.) for each part,
  then give ONE combined === QUESTIONS === section and ONE combined === ANSWERS === section at the end.
````

## Variations you can ask for

- *"Same topic again but harder: more self-corrections and two similar prices."*
- *"Give me Part 1 practice that focuses only on spelling names and addresses."*
- *"Write a Part 4 lecture on a medical topic (e.g. how vaccines train the immune system)."* Great for building vocabulary for tech + healthcare research.
- *"Find a real IELTS-style listening transcript on X and convert it into this format."*

## Format reference (what the tool understands)

| You write | The tool does |
|---|---|
| `Sam: Hello` | Sam's voice says "Hello" |
| a line with no label | the **Narrator** reads it (or it continues the previous speaker's lecture) |
| `[Pause: you now have 30 seconds to ...]` | narrator reads it, then **30 s of real silence** |
| `[Pause 5]` | 5 s of silence, nothing read |
| `W-H-I-T-F-I-E-L-D` | spelled clearly, letter by letter |
| `0412 556 789` | read digit by digit ("oh four one two...") |
| `Title: ...` | name of the test |
| `Voices: Sam=bm_lewis, Clara=bf_emma` | forces voices (otherwise auto-cast; change them in Studio) |
| `=== QUESTIONS ===` | question paper shown in Exam and Practice; `N ____` becomes an answer box |
| `=== ANSWERS ===` | answer key used for marking (never shown until you submit) |

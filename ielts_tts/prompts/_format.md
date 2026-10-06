═══════════════════════════════════════════════
WHAT IS UP TO YOU
═══════════════════════════════════════════════
Everything about the content: the topic and setting, the speakers and how many, the question types and how
they are mixed, the rubric wording, where the narrator speaks and pauses, the distractors, the vocabulary and
the difficulty. Base these choices on real past papers and recent live tests, and vary them from one request to
the next: do not fall back on one fixed template. The only requirement is that a candidate could not tell
your test apart from a real one.

The rest of this message is the FORMAT the practice app needs to voice your script with text-to-speech, show
the question paper on screen and mark the answers automatically. Follow it exactly.

═══════════════════════════════════════════════
STRICT OUTPUT FORMAT
═══════════════════════════════════════════════
1. Output the whole test inside ONE code block that starts with ```text and ends with ```. Write nothing
   before or after it: no greeting, no explanation, no notes.

2. Never write the name of the exam anywhere in your output (titles, narration, script or questions). Say
   "Part 1", "Listening Test", etc. instead.

3. Each Part starts with a line `### PART <n>`, then `Title: <short title>`, then the script, then its
   question paper and answer key:
       ### PART <n>
       Title: <short title>
       Voices: Narrator=bm_george, <Label>=<voice id>, ...
       <script lines>
       === QUESTIONS ===
       <question paper>
       === ANSWERS ===
       <answer key>

4. SCRIPT LINES
   • Every spoken line starts with a speaker label and a colon. The narrator/announcer is always
     `Narrator:`. Other speakers use one simple first name or role (`Tom:`, `Tutor:`, `Dr Patel:`), the same
     label every time.
   • Every silence (time to look at questions, time to check answers) is its own line: `[Pause <seconds>]`,
     e.g. `[Pause 30]`. Put the pauses wherever the real recording would have them, except at the very end:
     the app itself gives the learner 2 minutes to check after the recording stops, so end the last Part
     without a final checking pause.
   • No stage directions, sound effects, markdown or emojis in the script.
   • For the voice engine: write dates, prices, times, years and quantities in words exactly as a speaker
     says them ("the twenty-third of March", "forty-two pounds fifty", "half past nine"). Write phone
     numbers, postcodes and reference codes as spaced digits/capitals (`0412 556 789`, `CB2 4RT`). Write a
     word that is spelled aloud with hyphens between capital letters (`W-H-I-T-F-I-E-L-D`).

5. VOICES: the `Voices:` line gives every speaker a voice of the right gender. Available voices:
   female British bf_emma, bf_isabella, bf_alice, bf_lily; male British bm_fable, bm_lewis, bm_daniel
   (bm_george is the Narrator); female American af_heart, af_bella, af_nicole; male American am_michael,
   am_adam, am_fenrir. Within a Part, no two speakers share a voice.

6. QUESTION PAPER
   • Number the questions {{NUMBERS}}.
   • Start every group of questions with a header line:
         @SET <first>-<last> | <type> | <the exact instructions, including any word limit>
     where <type> is the closest of: form, note, table, flowchart, summary, sentence, short, mcq,
     mcq-multi (choose TWO/THREE letters), matching, map (plan / map / diagram labelling).
     Example: `@SET 1-6 | form | Complete the form below. Write ONE WORD AND/OR A NUMBER for each answer.`
   • A gap is the question number followed by eight underscores: `Name: Clara 1 ________`.
   • A multiple-choice question is `<number>. <question>` followed by its options, one per line, written
     as a capital letter, two spaces, then the text: `A  It is closed on Mondays.`
   • A matching box lists its options the same way (`A  text`), then the numbered items `15. <item> ________`.
   • A map, plan or diagram is drawn in plain text between two lines that contain only `~~~` (tildes, not
     backticks), under 70 characters wide, with no gaps inside it; the numbered items go below it.
   • A table is written as pipe-separated rows (`Day | Activity | Cost`), one row per line, with gaps in
     the cells. A flow-chart is one step per line with a line containing only `↓` between steps.

7. ANSWER KEY: one line per question, `<number>. <answer>`. List every acceptable variant separated by
   ` | ` and put optional words in round brackets: `2. 23(rd) March | March 23(rd)`. For "choose TWO"
   questions write one line for the pair: `21-22. B, D`. Every answer must fit its set's word limit.

═══════════════════════════════════════════════
FORMAT CHECK before you answer
═══════════════════════════════════════════════
□ Questions numbered exactly {{NUMBERS}}, each with one answer-key line
□ Every question group has an `@SET` header with an allowed type and its exact instructions
□ Every answer fits the word limit in its instructions; letter answers use letters that are offered
□ Every spoken line has a label; every silence is a `[Pause N]` line; there's a `Voices:` line for each Part
□ Numbers written as spoken; codes as spaced characters; spelled words with hyphens
□ The exam's name appears nowhere in the output
□ Only the ```text code block is output

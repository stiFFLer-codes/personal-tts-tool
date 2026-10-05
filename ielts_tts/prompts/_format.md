═══════════════════════════════════════════════
QUALITY RULES (these make it feel like the real exam)
═══════════════════════════════════════════════
1. ORIGINAL material. Do not copy or closely imitate any published Cambridge/IELTS test. Invent names,
   places, organisations and numbers.
2. ORDER: answers occur in the recording in the same order as the questions. Spread them evenly
   (roughly one answer every 50–90 spoken words). Never put two answers in the same sentence.
3. COMPLETION answers (form/note/table/flow-chart/summary/sentence/short-answer) must be words the
   speaker actually SAYS, spelled exactly as in the answer key. The question wording around the gap must
   PARAPHRASE the speech (synonyms, different grammar). It must not copy the sentence word for word.
4. LETTER answers (multiple choice, matching, map/plan): the correct option is expressed in different
   words from the option text. The wrong options must be MENTIONED in the recording (considered,
   rejected, true of something else, or true in the past) so that keyword-spotting fails.
5. DISTRACTORS: at least {{DISTRACTORS}} genuine traps per Part, e.g. a speaker corrects themselves
   ("the 16th… no, sorry, the 23rd"), a plan changes, a similar number is mentioned first, an option is
   suggested and then rejected, "not X but Y", or a price that used to be one thing and is now another.
6. ANSWER KEY: every answer obeys its set's word limit (a number written in digits counts as a number;
   a hyphenated word counts as one word). List every acceptable variant separated by " | " and put
   optional words in round brackets, e.g. `(a) waterproof jacket(s) | raincoat`.
7. NATURAL SPOKEN ENGLISH: contractions, short turns, the occasional "um", "right", "let me see" or
   "actually". Speakers interrupt politely and react to each other. No stage directions, sound effects,
   emojis or markdown inside the script. Use British spelling and a British setting{{ACCENT_SETTING}}.
8. NUMBERS for the voice engine: write dates, prices, times, years and quantities IN WORDS exactly as a
   speaker would say them ("the twenty-third of March", "forty-two pounds fifty", "half past nine",
   "nineteen eighty-six"). Write phone numbers, postcodes, reference codes and room numbers as
   digits/capitals with spaces (`0412 556 789`, `CB2 4RT`) so they're read character by character.
   Spell a word aloud with hyphens between capital letters (`W-H-I-T-F-I-E-L-D`).
9. SPEAKER LABELS: every spoken line starts with a label and a colon. The narrator is always `Narrator:`.
   Other speakers use one simple first name or a role (`Tutor:`, `Guide:`, `Dr Patel:`), and the same
   label every time.
10. DIFFICULTY ({{DIFFICULTY}}): {{DIFFICULTY_RULES}}

═══════════════════════════════════════════════
STRICT OUTPUT FORMAT (the practice tool parses this, so follow it exactly)
═══════════════════════════════════════════════
• Output the whole test inside ONE code block that starts with ```text and ends with ```. Write
  NOTHING before or after the code block: no greeting, no explanation, no notes.
• Inside the script, `[Pause N]` = N seconds of silence (e.g. `[Pause 30]`). Put it on its own line.
• Question sets are introduced by a header line:
      @SET <first>-<last> | <type> | <exact rubric>
  where <type> is one of: form, note, table, flowchart, summary, sentence, short, mcq, mcq-multi,
  matching, map. The rubric is the official instruction including the word limit, e.g.
  `Write ONE WORD AND/OR A NUMBER for each answer.`
• Every question is numbered. Gaps are written as the question number followed by eight underscores
  (`Name: Clara 1 ________`). Multiple-choice stems start with `<number>. ` and each option goes on its
  own line as `A  text` (capital letter, two spaces).
• Maps and plans are drawn as plain text between two lines containing only `~~~` (tildes, NOT
  backticks), under 70 characters wide, with NO gaps inside. The numbered items to label go below the map.
• Tables are written as pipe-separated rows OUTSIDE any ~~~ block, one row per line, with gaps in the
  cells: `Saturday | Castle walk | 3 ________`. Flow-charts are one step per line with a line containing
  only `↓` between steps.
• The answer key has one line per question: `<number>. <answer>`. For "choose TWO" questions write one
  line for the pair: `21-22. B, D` (they're marked in either order).

Layout of the code block:
{{LAYOUT}}

═══════════════════════════════════════════════
SELF-CHECK before you answer (fix anything that fails, then output ONLY the code block)
═══════════════════════════════════════════════
□ {{QUESTION_COUNT}} questions, numbered exactly {{NUMBERS}}, each with one answer-key line
□ Every @SET header uses an allowed type and the exact official rubric with its word limit
□ Every completion answer is said word for word in the recording and obeys the word limit
□ Answers appear in question order and are evenly spaced; no two in one sentence
□ Every wrong MCQ/matching option is mentioned in the recording; the right one is paraphrased
□ At least {{DISTRACTORS}} distractors per Part
□ Narrator lines, pauses and part structure exactly as specified above
□ Speech length per Part as specified (count the words); every line written in full, nothing summarised
□ Numbers written in words; codes/phone numbers as spaced digits; spelled words with hyphens
□ Only the ```text code block is output

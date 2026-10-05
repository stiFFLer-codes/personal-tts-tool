/* IELTS Listening Studio: front end. Vanilla JS, no dependencies, works offline. */
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const el = (tag, { dataset, ...props } = {}, ...kids) => {
  const node = Object.assign(document.createElement(tag), props);
  if (dataset) Object.assign(node.dataset, dataset);
  for (const kid of kids) if (kid != null) node.append(kid);
  return node;
};

const SPEAKER_COLOURS = ["#2f5bea", "#d9480f", "#0f8a6c", "#9c36b5", "#c2255c", "#1971c2", "#5c940d", "#e67700"];
const NARRATOR = "Narrator";
const TASK_IDS = ["part1", "part2", "part3", "part4", "full"];

/* What each task page teaches. From the official test format + recent Cambridge papers. */
const TASKS = {
  part1: {
    eyebrow: "Part 1 · Questions 1–10 · Everyday social", title: "Conversation",
    lede: "Two people in an everyday situation: one books, enquires or registers; the other takes the details.",
    facts: [["Speakers", "2"], ["Audio", "4–6 min"], ["Difficulty", "Easiest"], ["Break", "Halfway"]],
    types: ["Form completion", "Note completion", "Table completion", "Multiple choice (sometimes)"],
    traps: ["Names spelled letter by letter (W-H-I-T-F-I-E-L-D)", "Numbers, dates and prices that get corrected (\"the 16th… no, the 23rd\")",
      "Plural -s and the word limit (ONE WORD AND/OR A NUMBER)"],
    tips: ["Use the reading time to predict each gap: a number? a name? a noun?", "Write names and numbers exactly as you hear them. Spelling counts.",
      "Don't write the first number you hear. Wait for the speaker to confirm it."],
  },
  part2: {
    eyebrow: "Part 2 · Questions 11–20 · Everyday social", title: "Monologue",
    lede: "One speaker (a guide, presenter or manager) gives practical information to a group or to listeners.",
    facts: [["Speakers", "1"], ["Audio", "4–6 min"], ["Difficulty", "Easy–medium"], ["Break", "Halfway"]],
    types: ["Multiple choice", "Map / plan labelling", "Matching", "Choose TWO letters", "Note completion"],
    traps: ["Options that are mentioned but rejected, or that used to be true", "Directions on the map (opposite, beyond, at the end of)",
      "Something true for one group but not another"],
    tips: ["Before the audio, find ★ on the map and the landmarks around it.", "Follow the speaker's route. The places come in question order.",
      "Cross out MCQ options as the speaker rules them out."],
  },
  part3: {
    eyebrow: "Part 3 · Questions 21–30 · Educational", title: "Discussion",
    lede: "Two to four people (students, often with a tutor) discuss an assignment, project or research.",
    facts: [["Speakers", "2–4"], ["Audio", "4–6 min"], ["Difficulty", "Medium–hard"], ["Break", "Halfway"]],
    types: ["Multiple choice", "Matching", "Choose TWO letters", "Flow-chart completion", "Sentence completion"],
    traps: ["One speaker suggests something and the other rejects it", "The final decision differs from the first idea",
      "Opinions attributed to the wrong person"],
    tips: ["Track who says what. The voices differ, and so do their views.", "Listen for agreement signals: \"Exactly\", \"I'm not sure about that\", \"Fair point, but…\"",
      "Questions usually ask about what they finally decide or believe."],
  },
  part4: {
    eyebrow: "Part 4 · Questions 31–40 · Academic", title: "Lecture",
    lede: "One speaker gives a university lecture or presentation. No interruptions and no break in the middle.",
    facts: [["Speakers", "1"], ["Audio", "5–7 min"], ["Difficulty", "Hardest"], ["Break", "None"]],
    types: ["Note completion (ONE WORD ONLY)", "Summary completion", "Flow-chart completion", "Table / sentence completion"],
    traps: ["A related term said just before or after the answer", "A common misconception given before the real fact",
      "No break: miss one and the next answer is already coming"],
    tips: ["Use the reading time to read all ten gaps and the headings.", "Headings match the lecturer's signposts (\"Turning now to…\").",
      "Missed one? Let it go immediately and listen for the next."],
  },
  full: {
    eyebrow: "Full Test · Questions 1–40 · Computer-delivered", title: "Exam simulation",
    lede: "All four Parts in one sitting, exactly like test day: about 30 minutes, heard once, 40 questions, band score.",
    facts: [["Parts", "4"], ["Questions", "40"], ["Audio", "~30 min"], ["Checking", "30 s per Part + 2 min"]],
    types: ["Every question type in the real-paper mix", "Parts get harder from 1 to 4", "Band score estimate at the end"],
    traps: ["Losing focus in Parts 3–4", "Spending check time on one missed answer", "Breaking the word limit"],
    tips: ["Sit it in one go with headphones: no pausing, no phone.", "Use each 30 s check to fix spelling, then move on.",
      "Afterwards, open Progress to see which question types cost you marks."],
  },
  custom: {
    eyebrow: "Custom script", title: "Any listening script",
    lede: "Paste a script from a book, a website or an older prompt. The format is flexible; checks are advice only.",
  },
};

const TYPE_LABELS = {
  form: "Form completion", note: "Note completion", table: "Table completion", flowchart: "Flow-chart completion",
  summary: "Summary completion", sentence: "Sentence completion", short: "Short-answer questions",
  mcq: "Multiple choice", "mcq-multi": "Choose TWO letters", matching: "Matching", map: "Map / plan labelling",
  other: "Untagged questions",
};
// Where to drill each question type (it's most common in this Part).
const DRILL = { form: "part1", table: "part1", note: "part4", summary: "part4", flowchart: "part3", sentence: "part3",
  mcq: "part3", "mcq-multi": "part3", matching: "part3", map: "part2", short: "part1" };

const state = {
  ready: false, mp3: false, voices: [], tasks: null,
  route: "home", task: "part1",
  drafts: {},            // per-task script text
  prompts: {},           // per-task built prompt
  parsed: null, castChoice: {},
  test: null, tests: [], library: [],
  examRunning: false, examPart: 0,
};

const store = {
  get(key, fallback) { try { const v = localStorage.getItem(key); return v == null ? fallback : JSON.parse(v); } catch { return fallback; } },
  set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode */ } },
};

async function api(path, body) {
  const res = await fetch(path, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function toast(message, ms = 2600) {
  const t = $("#toast");
  t.textContent = message;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (t.hidden = true), ms);
}

const fmt = (sec) => {
  sec = Math.max(0, Math.floor(sec || 0));
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;
};
const pct = (a, b) => (b ? Math.round((100 * a) / b) : 0);
const kindLabel = (k) => ({ part1: "Part 1", part2: "Part 2", part3: "Part 3", part4: "Part 4", full: "Full test" }[k] || "Custom");

function speakerColour(name, test = state.test) {
  if (name === NARRATOR) return "#6a7180";
  const order = test ? Object.keys(test.cast).filter((s) => s !== NARRATOR) : [];
  const i = order.indexOf(name);
  return SPEAKER_COLOURS[(i < 0 ? 0 : i) % SPEAKER_COLOURS.length];
}

/* ================================ routing ================================ */
function go(route) { location.hash = route; }

function showRoute(route) {
  if (!route || !(TASK_IDS.includes(route) || ["home", "custom", "practice", "exam", "progress"].includes(route))) route = "home";
  if (state.examRunning && route !== "exam") {
    if (!confirm("Leave the exam? The recording will stop and this attempt won't be marked.")) { history.replaceState(null, "", "#exam"); return; }
    stopExam();
  }
  state.route = route;
  const isTask = TASK_IDS.includes(route) || route === "custom";
  $$(".view").forEach((v) => v.classList.toggle("active",
    v.id === (isTask ? "view-task" : `view-${route}`)));
  $$(".nav a").forEach((a) => a.classList.toggle("active", a.dataset.route === route));
  if (route !== "practice") practiceAudio.pause();
  if (isTask) openTask(route);
  if (route === "home") renderHome();
  if (route === "progress") loadHistory();
  if (route === "exam" && !state.examRunning) showExamIntro();
  window.scrollTo({ top: 0 });
}
window.addEventListener("hashchange", () => showRoute(location.hash.slice(1)));
document.addEventListener("click", (e) => {
  const target = e.target.closest("[data-goto]");
  if (target) go(target.dataset.goto);
});

/* ================================ status ================================ */
async function loadStatus() {
  const s = await api("/api/status");
  state.ready = s.ready;
  state.mp3 = s.mp3;
  const pill = $("#status");
  pill.textContent = s.ready ? `Offline voices ready · ${s.model.includes("int8") ? "small" : "full"} model` : "Voice model missing";
  pill.className = `pill ${s.ready ? "ok" : "bad"}`;
  $("#model-banner").hidden = s.ready;
  if (s.ready) {
    try { state.voices = (await api("/api/voices")).voices; } catch (err) { toast(err.message); }
  }
}

/* ================================ home ================================ */
function renderHome() {
  const box = $("#task-cards");
  box.replaceChildren();
  const history = state.history || [];
  for (const id of TASK_IDS) {
    const info = TASKS[id];
    const done = history.filter((h) => h.kind === id);
    let stat = "Not tried yet";
    if (id === "full") {
      const bands = done.filter((h) => h.band != null).map((h) => h.band);
      if (done.length) stat = `${done.length} test${done.length === 1 ? "" : "s"} · best band ${bands.length ? Math.max(...bands).toFixed(1) : "—"}`;
    } else {
      // Parts are practised on their own and inside full tests.
      const n = id.slice(-1);
      let right = 0, total = 0;
      for (const h of history) if (h.by_part?.[n]) { right += h.by_part[n][0]; total += h.by_part[n][1]; }
      if (total) stat = `${pct(right, total)}% correct over ${total} questions`;
    }
    const card = el("a", { className: `task-card ${id}`, href: `#${id}` },
      el("div", { className: "tc-eyebrow", textContent: info.eyebrow.split(" · ").slice(0, 2).join(" · ") }),
      el("div", { className: "tc-title", textContent: id === "full" ? "🏁 Full Test" : `${kindLabel(id)} · ${info.title}` }),
      el("p", { className: "tc-lede", textContent: info.lede }),
      el("div", { className: "tc-types", textContent: info.types.slice(0, 3).join(" · ") }),
      el("div", { className: "tc-stat", textContent: stat }));
    box.append(card);
  }
}

/* ================================ task pages ================================ */
const scriptBox = $("#script");
let parseTimer;

function openTask(task) {
  // Save the draft of the page we're leaving.
  if (state.task && state.task !== task) state.drafts[state.task] = scriptBox.value;
  const switched = state.task !== task;
  state.task = task;
  const info = TASKS[task];
  $("#t-eyebrow").textContent = info.eyebrow;
  $("#t-title").textContent = task === "custom" ? info.title : `${kindLabel(task)} · ${info.title}`;
  $("#t-lede").textContent = info.lede;
  const isTask = task !== "custom";
  $("#t-guide").hidden = !isTask;
  $("#t-step-prompt").hidden = !isTask;
  $("#t-paste-no").textContent = isTask ? "2" : "1";
  $("#t-gen-no").textContent = isTask ? "3" : "2";
  if (isTask) { renderGuide(info); setupPromptControls(task); }
  $("#t-recent-title").textContent = isTask ? `Your ${kindLabel(task)} recordings` : "All recordings";
  if (switched) {
    scriptBox.value = state.drafts[task] ?? store.get(`draft:${task}`, "");
    state.castChoice = {};
    $("#render-result").hidden = true;
    parseScript();
  }
  renderLibrary();
  renderRecent();
}

function renderGuide(info) {
  const g = $("#t-guide");
  g.replaceChildren(
    el("div", { className: "facts" }, ...info.facts.map(([k, v]) => el("div", { className: "fact" },
      el("span", { textContent: k }), el("b", { textContent: v })))),
    el("div", { className: "guide-cols" },
      el("div", {}, el("h3", { textContent: "Question types" }), el("ul", {}, ...info.types.map((t) => el("li", { textContent: t })))),
      el("div", {}, el("h3", { textContent: "Traps" }), el("ul", {}, ...info.traps.map((t) => el("li", { textContent: t })))),
      el("div", {}, el("h3", { textContent: "Strategy" }), el("ol", {}, ...info.tips.map((t) => el("li", { textContent: t }))))));
}

function setupPromptControls(task) {
  const focus = $("#t-focus");
  const options = state.tasks?.tasks[task]?.focus || [{ id: "mix", label: "Real exam mix" }];
  focus.replaceChildren(...options.map((o) => el("option", { value: o.id, textContent: o.label })));
  const saved = store.get(`prompt:${task}`, {});
  focus.value = options.some((o) => o.id === saved.focus) ? saved.focus : "mix";
  $("#t-focus-field").hidden = task === "full";
  $("#t-topic-field").querySelector("input").placeholder = task === "full"
    ? "Optional topic for Part 1 (the other Parts get random topics)" : "Leave empty for a random exam topic";
  $("#t-topic").value = saved.topic || "";
  $("#t-difficulty").value = saved.difficulty || "7-8";
  $("#t-accent").value = saved.accent || "british";
  if (state.prompts[task]) showPrompt(state.prompts[task]);
  else buildPrompt();
}

let promptTimer;
async function buildPrompt() {
  const task = state.task;
  if (!TASK_IDS.includes(task)) return;
  const params = { task, topic: $("#t-topic").value.trim(), focus: $("#t-focus").value || "mix",
    difficulty: $("#t-difficulty").value, accent: $("#t-accent").value };
  store.set(`prompt:${task}`, params);
  try {
    const result = await api(`/api/prompt?${new URLSearchParams(params)}`);
    if (state.task !== task) return;
    state.prompts[task] = result;
    showPrompt(result);
  } catch (err) { toast(err.message); }
}

function showPrompt(result) {
  $("#t-prompt").value = result.prompt;
  const plan = $("#t-plan");
  plan.replaceChildren();
  for (const [part, info] of Object.entries(result.plan)) {
    plan.append(el("span", { className: "chip" }, el("b", { textContent: `${kindLabel(part)}: ` }),
      `${info.topic} — ${info.summary}`));
  }
}

for (const id of ["#t-focus", "#t-difficulty", "#t-accent"]) $(id).addEventListener("change", buildPrompt);
$("#t-topic").addEventListener("input", () => { clearTimeout(promptTimer); promptTimer = setTimeout(buildPrompt, 500); });
$("#t-dice").addEventListener("click", async () => {
  if (state.task === "full") { $("#t-topic").value = ""; return buildPrompt(); }
  const { topic } = await api(`/api/topic?task=${state.task}`);
  $("#t-topic").value = topic;
  buildPrompt();
});
$("#t-new-prompt").addEventListener("click", () => { $("#t-topic").value = ""; buildPrompt(); });
$("#t-show-prompt").addEventListener("click", () => {
  const box = $("#t-prompt");
  box.hidden = !box.hidden;
  $("#t-show-prompt").textContent = box.hidden ? "👁 Show prompt" : "🙈 Hide prompt";
});
async function copyText(text, message) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {                                   // older browsers / no clipboard permission
    const tmp = el("textarea", { value: text, style: "position:fixed;opacity:0" });
    document.body.append(tmp);
    tmp.select();
    document.execCommand("copy");
    tmp.remove();
  }
  toast(message, 3500);
}
$("#t-copy").addEventListener("click", () => {
  const text = $("#t-prompt").value;
  if (text) copyText(text, "Prompt copied! Paste it into Claude, then paste Claude's reply below. 🚀");
});

scriptBox.addEventListener("input", () => {
  store.set(`draft:${state.task}`, scriptBox.value);
  clearTimeout(parseTimer);
  parseTimer = setTimeout(parseScript, 400);
});

async function parseScript() {
  const script = scriptBox.value;
  if (!script.trim()) {
    state.parsed = null;
    renderCheck();
    return;
  }
  try {
    state.parsed = await api("/api/parse", { script, kind: state.task });
    renderCheck();
  } catch (err) { toast(err.message); }
}

function voiceSelect(current) {
  const select = el("select");
  const groups = {};
  const list = state.voices.length ? state.voices
    : [...new Set(Object.values(state.parsed?.cast || {}))].map((id) => ({ id, label: id, accent: "Voices" }));
  for (const v of list) {
    groups[v.accent] ??= select.appendChild(el("optgroup", { label: v.accent }));
    groups[v.accent].append(el("option", { value: v.id, textContent: v.label, selected: v.id === current }));
  }
  return select;
}

let previewAudio = null;
function previewVoice(voice) {
  if (!state.ready) return toast("Download the voice model first (setup.bat).");
  previewAudio?.pause();
  previewAudio = new Audio(`/api/preview?voice=${encodeURIComponent(voice)}`);
  previewAudio.play().catch(() => toast("Couldn't play preview."));
}

function renderCheck() {
  const p = state.parsed;
  const cast = $("#cast"), stats = $("#stats"), list = $("#checklist");
  cast.replaceChildren(); stats.replaceChildren(); list.replaceChildren();
  const blocked = p && state.task !== "custom" && !p.checks.ok;
  $("#btn-generate").disabled = !p || !p.test.segments.some((s) => s.kind === "speech") || blocked;
  $("#btn-generate").textContent = blocked ? "Fix the ❌ items to generate" : "🎙️ Generate audio";
  if (!p) {
    $("#parsed-title").textContent = "Check & generate";
    list.append(el("p", { className: "muted small", textContent: "Paste Claude's reply on the left. The checks appear here." }));
    return;
  }

  const t = p.test;
  $("#parsed-title").textContent = t.title;
  const speech = t.segments.filter((s) => s.kind === "speech");
  const pauses = t.segments.filter((s) => s.kind === "pause");
  const words = speech.reduce((n, s) => n + s.text.split(/\s+/).length, 0);
  const estimate = words / 2.6 + pauses.reduce((n, s) => n + s.seconds, 0);  // ~155 wpm
  const chip = (label, value) => el("span", { className: "chip" }, `${label} `, el("b", { textContent: value }));
  stats.append(chip("Speakers", t.speakers.length), chip("Lines", speech.length),
    chip("Questions", t.question_numbers.length), chip("≈", fmt(estimate)));

  // Checklist: problems first, passed checks folded away.
  const items = p.checks.items;
  const problems = items.filter((i) => i.level !== "ok");
  const passed = items.filter((i) => i.level === "ok");
  const icon = { ok: "✅", warn: "⚠️", error: "❌" };
  if (state.task === "custom" && p.detected !== "custom") {
    list.append(el("div", { className: "check lvl-info" }, "💡 This looks like a ",
      el("a", { href: `#${p.detected}`, textContent: `${kindLabel(p.detected)} script` }),
      ". Paste it on that page for the full exam-format check."));
  }
  for (const i of problems) list.append(el("div", { className: `check lvl-${i.level}`, textContent: `${icon[i.level]} ${i.text}` }));
  const errors = problems.filter((i) => i.level === "error");
  if (errors.length && state.task !== "custom") {
    const ask = "Your IELTS script fails these format checks:\n" + errors.map((i) => `- ${i.text}`).join("\n") +
      "\nFix them, keep everything else the same, and send the whole corrected script again as one ```text code block.";
    list.append(el("button", { className: "ghost small-btn fix-btn", textContent: "📋 Copy fix request for Claude",
      onclick: () => copyText(ask, "Fix request copied. Paste it into the same Claude chat.") }));
  }
  if (passed.length) {
    const det = el("details", { className: "passed", open: !problems.length },
      el("summary", { textContent: `✅ ${passed.length} check${passed.length === 1 ? "" : "s"} passed` }),
      ...passed.map((i) => el("div", { className: "check lvl-ok", textContent: i.text })));
    list.append(det);
  }

  const people = [...(t.has_narrator ? [NARRATOR] : []), ...t.speakers];
  const fakeTest = { cast: Object.fromEntries(people.map((s) => [s, 1])) };
  for (const who of people) {
    const chosen = state.castChoice[who] || p.cast[who];
    const select = voiceSelect(chosen);
    select.addEventListener("change", () => { state.castChoice[who] = select.value; });
    const play = el("button", { className: "ghost", title: "Preview this voice", textContent: "▶" });
    play.addEventListener("click", () => previewVoice(select.value));
    const lines = speech.filter((s) => s.speaker === who).length;
    cast.append(el("div", { className: "cast-row", dataset: { speaker: who } },
      el("span", { className: "who" },
        el("span", { className: "dot", style: `background:${speakerColour(who, fakeTest)}` }),
        who, el("small", { textContent: ` · ${lines} line${lines === 1 ? "" : "s"}` })),
      select, play));
  }
}

function currentCast() {
  const out = {};
  for (const row of $$("#cast .cast-row")) out[row.dataset.speaker] = row.querySelector("select").value;
  return Object.keys(out).length ? out : (state.parsed?.cast || {});
}

$("#btn-generate").addEventListener("click", async () => {
  const btn = $("#btn-generate");
  btn.disabled = true;
  $("#render-result").hidden = true;
  $("#progress").hidden = false;
  setProgress(0, 0, "Starting…");
  try {
    const { job } = await api("/api/render", { script: scriptBox.value, cast: currentCast(), kind: state.task });
    const result = await pollJob(job);
    setTest(result);
    showRenderResult(result);
    await loadTests();
  } catch (err) {
    toast(err.message, 6000);
  } finally {
    $("#progress").hidden = true;
    btn.disabled = false;
  }
});

function setProgress(done, total, label) {
  $("#progress .bar").style.width = total ? `${(100 * done) / total}%` : "4%";
  $("#progress .label").textContent = label || `Rendering line ${done} of ${total}…`;
}

async function pollJob(id) {
  for (;;) {
    const job = await api(`/api/jobs/${id}`);
    if (job.state === "done") return job.result;
    if (job.state === "error") throw new Error(job.error);
    setProgress(job.done, job.total, job.total ? null : "Loading voices…");
    await new Promise((r) => setTimeout(r, 600));
  }
}

function showRenderResult(test) {
  $("#render-result").hidden = false;
  $("#result-text").textContent = `${test.title}: ${fmt(test.duration)} of audio ready`;
  $("#dl-wav").href = `${test.audio}?download`;
  $("#dl-mp3").hidden = !state.mp3;
  $("#dl-mp3").href = `/api/export/${test.id}.mp3`;
}

$("#btn-clear").addEventListener("click", () => {
  if (scriptBox.value.trim() && !confirm("Clear the script?")) return;
  scriptBox.value = "";
  store.set(`draft:${state.task}`, "");
  state.castChoice = {};
  parseScript();
  scriptBox.focus();
});

$("#btn-save").addEventListener("click", async () => {
  if (!scriptBox.value.trim()) return toast("Nothing to save yet.");
  try {
    const { file } = await api("/api/library", { script: scriptBox.value });
    toast(`Saved to library/${file}`);
    await loadLibrary();
    renderLibrary(file);
  } catch (err) { toast(err.message); }
});

async function loadLibrary() {
  state.library = (await api("/api/library")).items;
}

function renderLibrary(selected = "") {
  const items = state.task === "custom" ? state.library : state.library.filter((i) => i.kind === state.task);
  const select = $("#library-select");
  select.replaceChildren(el("option", { value: "", textContent: `📚 Library (${items.length})…` }));
  for (const item of items) select.append(el("option", { value: item.file, textContent: item.title, selected: item.file === selected }));
}
$("#library-select").addEventListener("change", async (e) => {
  const file = e.target.value;
  if (!file) return;
  if (scriptBox.value.trim() && !confirm("Replace the script in the editor?")) { e.target.value = ""; return; }
  const { script } = await api(`/api/library/${encodeURIComponent(file)}`);
  scriptBox.value = script;
  store.set(`draft:${state.task}`, script);
  state.castChoice = {};
  parseScript();
});

async function loadTests() {
  state.tests = (await api("/api/tests")).tests;
  renderRecent();
  for (const picker of $$(".test-picker")) {
    picker.replaceChildren(el("option", { value: "", textContent: "Choose a recording…" }));
    for (const t of state.tests) picker.append(el("option", { value: t.id, textContent: `${kindLabel(t.kind)} · ${t.title}`, selected: t.id === state.test?.id }));
  }
}

function renderRecent() {
  const recent = $("#recent");
  recent.replaceChildren();
  const mine = state.task === "custom" ? state.tests : state.tests.filter((t) => t.kind === state.task);
  if (!mine.length) recent.append(el("li", { className: "muted", textContent: "Nothing yet. Generate your first one above!" }));
  for (const t of mine.slice(0, 10)) {
    const best = t.best != null ? ` · best ${t.best}/${t.questions}` : "";
    const li = el("li", {},
      el("span", { textContent: t.title }),
      el("span", { className: "meta", textContent: `${fmt(t.duration)} · ${t.questions} Q${best} · ${t.created}` }),
      el("span", { className: "row gap" },
        el("button", { className: "ghost small-btn", textContent: "📝 Exam", onclick: () => openTest(t.id, "exam") }),
        el("button", { className: "ghost small-btn", textContent: "🎧", title: "Practice", onclick: () => openTest(t.id, "practice") })));
    recent.append(li);
  }
}

document.addEventListener("change", (e) => {
  if (e.target.matches(".test-picker") && e.target.value) openTest(e.target.value);
});

async function openTest(id, route) {
  try {
    setTest(await api(`/api/tests/${id}`));
    if (route) go(route);
    else if (state.route === "exam") showExamIntro();
  } catch (err) { toast(err.message); }
}

function setTest(test) {
  state.test = test;
  store.set("test", test.id);
  $$(".test-title").forEach((h) => (h.textContent = test.title));
  $$("[data-empty]").forEach((n) => (n.hidden = true));
  $$("[data-loaded]").forEach((n) => (n.hidden = false));
  $$(".test-picker").forEach((p) => (p.value = test.id));
  loadPractice(test);
}

/* ============================ questions widget ============================ */
// Turns the plain-text question paper into a real-looking paper with answer boxes:
//   "@SET 1-6 | form | Complete the form below…"  -> "Questions 1–6" heading + rubric
//   "Name: Clara 1 ________"                       -> inline box for Q1
//   "7. Why did the man…"                          -> box at the end of the line (MCQ letter)
//   "Day | Place | 3 ________"                     -> table row
//   ~~~ … ~~~                                       -> monospace map / plan
function renderQuestions(container, text, numbers, { editable = true } = {}) {
  container.replaceChildren();
  const placed = new Set();
  const gap = /(\d{1,2})\s*(?:_{2,}|…+|\.{4,})/g;
  const label = (n) => el("span", { className: "qnum", textContent: n });
  const input = (n) => {
    placed.add(n);
    return el("input", { className: "ans", type: "text", autocomplete: "off", spellcheck: false,
      disabled: !editable, dataset: { q: n } });
  };
  const withGaps = (target, line) => {
    let last = 0, m, any = false;
    gap.lastIndex = 0;
    while ((m = gap.exec(line))) {
      const n = Number(m[1]);
      if (!numbers.includes(n) || placed.has(n)) continue;
      target.append(line.slice(last, m.index), label(n), input(n));
      last = m.index + m[0].length;
      any = true;
    }
    if (any) target.append(line.slice(last));
    return any;
  };

  let currentSet = null, table = null, pre = null;
  const closeSet = () => {
    if (!currentSet) return;
    // Questions in this set without a box yet (e.g. "choose TWO") get boxes at the end of the set.
    const missing = [];
    for (let n = currentSet.start; n <= currentSet.end; n++) if (numbers.includes(n) && !placed.has(n)) missing.push(n);
    if (missing.length) {
      container.append(el("div", { className: "qline answers-row" }, el("span", { className: "muted small", textContent: "Your answers: " }),
        ...missing.flatMap((n) => [label(n), input(n)])));
    }
    currentSet = null;
  };

  for (let line of (text || "").split("\n")) {
    if (/^\s*(~~~|```)/.test(line)) {
      if (pre) { container.append(pre); pre = null; } else { pre = el("pre", { className: "qmap" }); }
      continue;
    }
    if (pre) { pre.append(line + "\n"); continue; }

    const set = line.match(/^\s*@SET\s+(\d{1,2})\s*(?:[-–]\s*(\d{1,2}))?\s*\|\s*([\w -]+?)\s*(?:\|\s*(.*))?$/i);
    if (set) {
      closeSet();
      table = null;
      const start = Number(set[1]), end = Number(set[2] || set[1]);
      currentSet = { start, end };
      const type = set[3].trim().toLowerCase();
      container.append(el("div", { className: "qset" },
        el("div", { className: "qset-title" }, el("b", { textContent: start === end ? `Question ${start}` : `Questions ${start}–${end}` }),
          el("span", { className: "chip type-chip", textContent: TYPE_LABELS[type] || type })),
        el("div", { className: "qrubric", textContent: set[4] || "" })));
      continue;
    }

    if ((line.match(/\|/g) || []).length >= 1 && /\S\s*\|\s*\S/.test(line)) {
      if (!table) { table = el("table", { className: "qtable" }); container.append(table); }
      const row = el("tr");
      for (const cell of line.split("|").map((c) => c.trim())) {
        const td = el(table.rows.length ? "td" : "th");
        if (!withGaps(td, cell)) td.append(cell);
        row.append(td);
      }
      table.append(row);
      continue;
    }
    table = null;

    // "22. ...the sleep 22 ________." -> drop the duplicate leading "22."
    const dup = line.match(/^\s*(\d{1,2})\s*[.)]\s+/);
    if (dup && new RegExp(`(?<!\\d)${dup[1]}\\s*(?:_{2,}|…+|\\.{4,})`).test(line.slice(dup[0].length))) line = line.slice(dup[0].length);
    const div = el("div", { className: "qline" });
    const trimmed = line.trim();
    if (trimmed === "↓") div.classList.add("qarrow");
    else if (/^questions?\s+\d/i.test(trimmed) || (trimmed.length > 3 && trimmed === trimmed.toUpperCase() && /[A-Z]{2}/.test(trimmed))) div.classList.add("qhead");
    if (/^[A-L](?:\s{2,}|[.)]\s+)\S/.test(trimmed)) div.classList.add("qopt");

    if (withGaps(div, line)) { container.append(div); continue; }
    const lead = line.match(/^\s*(\d{1,2})\s*[.)]\s/);
    const n = lead ? Number(lead[1]) : null;
    if (n && numbers.includes(n) && !placed.has(n)) {
      const body = line.slice(lead[0].length);
      const blank = body.match(/_{2,}|…+/);
      div.append(label(n));
      if (blank) div.append(body.slice(0, blank.index), input(n), body.slice(blank.index + blank[0].length));
      else div.append(body, " ", input(n));
    } else {
      div.append(line || " ");
    }
    container.append(div);
  }
  if (pre) container.append(pre);
  closeSet();

  const leftovers = numbers.filter((n) => !placed.has(n));
  if (leftovers.length) {
    const extra = el("div", { className: "extra-answers" }, el("div", { className: "qhead", textContent: "Answer sheet" }));
    for (const n of leftovers) extra.append(el("div", { className: "qline" }, label(n), input(n)));
    container.append(extra);
  }
}

const collectAnswers = (container) =>
  Object.fromEntries($$("input.ans", container).map((i) => [i.dataset.q, i.value]));

function paperParts(test) {
  // Multi-part tests show one Part per page; single tests show everything.
  if (test.parts?.length > 1) return test.parts.map((p) => ({ n: p.n, questions: p.questions, numbers: p.numbers, start: p.start, end: p.end }));
  return [{ n: test.parts?.[0]?.n || 0, questions: test.questions, numbers: test.question_numbers, start: 0, end: test.duration }];
}

function renderPaper(container, test, opts) {
  container.replaceChildren();
  const parts = paperParts(test);
  for (const p of parts) {
    const page = el("div", { className: "paper-part", dataset: { part: p.n } });
    if (parts.length > 1) page.append(el("h3", { className: "paper-title", textContent: `Part ${p.n}` }));
    const body = el("div");
    renderQuestions(body, p.questions || "(No question paper in this script, just listen.)", p.numbers, opts);
    page.append(body);
    container.append(page);
  }
  return parts;
}

function partTabs(box, parts, onPick) {
  box.replaceChildren();
  box.hidden = parts.length < 2;
  for (const p of parts) {
    box.append(el("button", { className: "part-tab", textContent: `Part ${p.n}`, dataset: { part: p.n }, onclick: () => onPick(p.n) }));
  }
}

function showPaperPart(container, tabs, n) {
  $$(".paper-part", container).forEach((pg) => (pg.hidden = $$(".paper-part", container).length > 1 && Number(pg.dataset.part) !== n));
  $$(".part-tab", tabs).forEach((b) => b.classList.toggle("active", Number(b.dataset.part) === n));
}

/* ================================ practice ================================ */
const practiceAudio = new Audio();
practiceAudio.preload = "auto";
let currentLine = -1;
let loopLine = false;
let practicePart = 0;

function transcriptItems(list, test, { clickable }) {
  list.replaceChildren();
  let lastPart = null;
  const multi = test.parts?.length > 1;
  test.timeline.forEach((item, idx) => {
    if (multi && item.part !== lastPart) {
      lastPart = item.part;
      list.append(el("li", { className: "part-sep", textContent: `Part ${item.part}`, dataset: { partStart: item.part } }));
    }
    const li = el("li", { className: item.kind, dataset: { idx } });
    if (item.kind === "pause") {
      li.append(el("span", { className: "t", textContent: fmt(item.start) }),
        el("span", { className: "spk", textContent: "⏸" }),
        el("span", { className: "txt", textContent: `${item.seconds} s pause` }));
    } else {
      li.append(el("span", { className: "t", textContent: fmt(item.start) }),
        el("span", { className: "spk", textContent: item.speaker, style: `background:${speakerColour(item.speaker, test)}` }),
        el("span", { className: "txt", textContent: item.text }));
    }
    if (clickable) li.addEventListener("click", () => {
      if ($("#p-blind").checked && item.kind === "speech" && !li.classList.contains("revealed")) {
        li.classList.add("revealed");
        return;
      }
      seekTo(item.start, true);
    });
    list.append(li);
  });
}

function loadPractice(test) {
  practiceAudio.pause();
  practiceAudio.src = test.audio;
  practiceAudio.playbackRate = Number($("#p-speed").value);
  currentLine = -1;
  transcriptItems($("#p-transcript"), test, { clickable: true });
  const hasQ = test.question_numbers.length > 0;
  $("#p-questions-card").hidden = !hasQ || !$("#p-showq").checked;
  const parts = renderPaper($("#p-questions"), test, { editable: true });
  practicePart = parts[0].n;
  partTabs($("#p-parts"), parts, (n) => {
    const part = parts.find((p) => p.n === n);
    seekTo(part.start);
    setPracticePart(n);
  });
  setPracticePart(practicePart);
  updateClock();
}

function setPracticePart(n) {
  practicePart = n;
  showPaperPart($("#p-questions"), $("#p-parts"), n);
  $("#p-q-title").textContent = state.test?.parts?.length > 1 ? `Questions · Part ${n}` : "Questions";
}

function seekTo(t, play = false) {
  practiceAudio.currentTime = Math.max(0, t);
  if (play) practiceAudio.play();
  updateClock();
}

function lineAt(t) {
  const tl = state.test?.timeline || [];
  let found = -1;
  for (let i = 0; i < tl.length; i++) if (tl[i].start <= t + 0.05) found = i;
  return found;
}

function updateClock() {
  const t = practiceAudio.currentTime, d = practiceAudio.duration || state.test?.duration || 0;
  $("#p-time").textContent = `${fmt(t)} / ${fmt(d)}`;
  if (!seeking) $("#p-seek").value = d ? Math.round((t / d) * 1000) : 0;
  $("#p-play").textContent = practiceAudio.paused ? "▶" : "⏸";

  const idx = lineAt(t);
  if (loopLine && currentLine >= 0) {
    const item = state.test.timeline[currentLine];
    if (t >= item.end + 0.25) { practiceAudio.currentTime = item.start; return; }
  }
  if (idx !== currentLine) {
    currentLine = idx;
    $$("#p-transcript li").forEach((li) => li.classList.toggle("current", Number(li.dataset.idx) === idx && li.dataset.idx !== undefined));
    const cur = $(`#p-transcript li[data-idx="${idx}"]`);
    if (cur && !practiceAudio.paused) cur.scrollIntoView({ block: "nearest", behavior: "smooth" });
    const part = state.test?.timeline[idx]?.part;
    if (part && part !== practicePart && state.test.parts?.length > 1) setPracticePart(part);
  }
}

let seeking = false;
let rafId = 0;
const tick = () => { updateClock(); if (!practiceAudio.paused) rafId = requestAnimationFrame(tick); };
practiceAudio.addEventListener("play", () => { cancelAnimationFrame(rafId); tick(); });
practiceAudio.addEventListener("pause", updateClock);
practiceAudio.addEventListener("loadedmetadata", updateClock);
practiceAudio.addEventListener("seeked", updateClock);

$("#p-seek").addEventListener("input", (e) => {
  seeking = true;
  const d = practiceAudio.duration || 0;
  $("#p-time").textContent = `${fmt((e.target.value / 1000) * d)} / ${fmt(d)}`;
});
$("#p-seek").addEventListener("change", (e) => {
  seeking = false;
  seekTo((e.target.value / 1000) * (practiceAudio.duration || 0));
});

function togglePlay() { practiceAudio.paused ? practiceAudio.play() : practiceAudio.pause(); }
function stepLine(dir) {
  const tl = state.test?.timeline || [];
  const t = practiceAudio.currentTime;
  const idx = lineAt(t);
  if (dir < 0 && idx >= 0 && t - tl[idx].start > 1.2) return seekTo(tl[idx].start);
  let next = idx + dir;
  while (next >= 0 && next < tl.length && tl[next].kind !== "speech") next += dir;
  if (next >= 0 && next < tl.length) seekTo(tl[next].start);
  else if (dir < 0) seekTo(0);
}
function replayLine() {
  const idx = lineAt(practiceAudio.currentTime);
  if (idx >= 0) seekTo(state.test.timeline[idx].start, true);
}
function toggleLoop() {
  loopLine = !loopLine;
  $("#p-loop").classList.toggle("on", loopLine);
  toast(loopLine ? "Looping the current line" : "Loop off", 1200);
}

$("#p-play").addEventListener("click", togglePlay);
$("#p-prev").addEventListener("click", () => stepLine(-1));
$("#p-next").addEventListener("click", () => stepLine(1));
$("#p-replay").addEventListener("click", replayLine);
$("#p-loop").addEventListener("click", toggleLoop);
$("#p-speed").addEventListener("change", (e) => { practiceAudio.playbackRate = Number(e.target.value); store.set("speed", e.target.value); });
$("#p-blind").addEventListener("change", (e) => {
  $("#view-practice").classList.toggle("blind", e.target.checked);
  $$("#p-transcript li.revealed").forEach((li) => li.classList.remove("revealed"));
});
$("#p-showq").addEventListener("change", (e) => {
  $("#p-questions-card").hidden = !e.target.checked || !state.test?.question_numbers.length;
});

document.addEventListener("keydown", (e) => {
  if (state.route !== "practice" || !state.test) return;
  if (e.target.closest("input, textarea, select") || e.ctrlKey || e.metaKey || e.altKey) return;
  const actions = {
    " ": togglePlay, ArrowLeft: () => stepLine(-1), ArrowRight: () => stepLine(1),
    r: replayLine, R: replayLine, l: toggleLoop, L: toggleLoop,
    b: () => $("#p-blind").click(), B: () => $("#p-blind").click(),
  };
  if (actions[e.key]) { e.preventDefault(); actions[e.key](); }
});

/* ================================ exam ================================ */
const examAudio = new Audio();
let checkTimer = 0;
let examParts = [];
let playingPart = 0;        // the paper turns the page when the audio enters a new Part, nothing more
const CHECK_SECONDS = 120;

function showExamIntro() {
  const t = state.test;
  $("#e-intro").hidden = false;
  $("#e-live").hidden = true;
  $("#e-results").hidden = true;
  if (!t) return;
  const n = t.question_numbers.length;
  const multi = t.parts?.length > 1;
  $("#e-meta").textContent = `${kindLabel(t.kind)} · ${fmt(t.duration)} of audio · ${n} question${n === 1 ? "" : "s"}`;
  $("#e-noanswers").hidden = n > 0;
  const rules = [
    "🔊 The recording plays <b>once</b>, just like the real test. No pausing, no rewinding.",
    "✍️ Type your answers while you listen. Spelling counts, capitals don't, and answers over the word limit are wrong.",
    multi ? "⏸ The audio has the real 30-second checks after Parts 1–3. The question paper switches Part automatically; click a Part to look ahead or back."
      : "📄 Reading time before the questions is built into the audio, like the real test.",
    "⏱️ When the audio ends you get <b>2 minutes</b> to check (computer-delivered timing), then it's marked.",
  ];
  $("#e-rules").innerHTML = rules.map((r) => `<li>${r}</li>`).join("");
}

$("#e-start").addEventListener("click", () => {
  const t = state.test;
  if (!t) return;
  practiceAudio.pause();
  state.examRunning = true;
  $("#e-intro").hidden = true;
  $("#e-live").hidden = false;
  $("#e-submit").hidden = true;
  $("#e-state").textContent = "● Playing";
  $("#e-state").classList.remove("done");
  examParts = renderPaper($("#e-questions"), t, { editable: true });
  partTabs($("#e-parts"), examParts, setExamPart);
  playingPart = examParts[0].n;
  setExamPart(playingPart);
  examAudio.src = t.audio;
  examAudio.currentTime = 0;
  examAudio.volume = Number($("#e-volume").value);
  examAudio.play().catch(() => toast("Click Start again: the browser blocked autoplay."));
  $("#e-questions input.ans")?.focus();
});

function setExamPart(n) {
  state.examPart = n;
  showPaperPart($("#e-questions"), $("#e-parts"), n);
}

examAudio.addEventListener("timeupdate", () => {
  const d = examAudio.duration || state.test?.duration || 1;
  const now = examAudio.currentTime;
  $("#e-track").style.width = `${(100 * now) / d}%`;
  $("#e-time").textContent = `${fmt(now)} / ${fmt(d)}`;
  if (examParts.length > 1) {
    const playing = [...examParts].reverse().find((p) => now >= p.start - 0.5);
    if (playing && playing.n !== playingPart) {
      playingPart = playing.n;
      setExamPart(playing.n);
    }
    $$(".part-tab", $("#e-parts")).forEach((b) => b.classList.toggle("playing", Number(b.dataset.part) === playingPart));
  }
});
// Strict mode: the recording can't be paused or scrubbed (media keys, etc.).
examAudio.addEventListener("pause", () => {
  if (state.examRunning && !examAudio.ended && examAudio.currentTime > 0) examAudio.play();
});
examAudio.addEventListener("ended", () => {
  if (!state.examRunning) return;
  if (!state.test.question_numbers.length) { stopExam(); showExamIntro(); toast("Recording finished."); return; }
  let left = CHECK_SECONDS;
  const label = $("#e-state");
  label.classList.add("done");
  $("#e-submit").hidden = false;
  const tickDown = () => {
    label.textContent = `✓ Audio finished. Check your answers: ${fmt(left)}`;
    if (left-- <= 0) submitExam();
  };
  tickDown();
  checkTimer = setInterval(tickDown, 1000);
});
$("#e-volume").addEventListener("input", (e) => (examAudio.volume = Number(e.target.value)));
$("#e-submit").addEventListener("click", submitExam);
$("#e-retry").addEventListener("click", showExamIntro);

function stopExam() {
  state.examRunning = false;
  clearInterval(checkTimer);
  examAudio.pause();
}

async function submitExam() {
  if (!state.examRunning) return;
  const answers = collectAnswers($("#e-questions"));
  stopExam();
  try {
    const result = await api("/api/grade", { id: state.test.id, answers });
    showResults(result);
    loadTests();
    api("/api/history").then((r) => (state.history = r.history));
  } catch (err) {
    toast(err.message, 5000);
    showExamIntro();
  }
}

function cheer(ratio) {
  if (ratio === 1) return "Perfect score! Band 9 energy. Erasmus committee, take note. 🏆";
  if (ratio >= 0.85) return "Excellent! That's band 8+ territory. Keep this streak alive. 🔥";
  if (ratio >= 0.7) return "Solid work! Review the misses in Practice and you'll close the gap. 💪";
  if (ratio >= 0.5) return "Good base. Replay the lines you missed with the transcript, then retake tomorrow. 📈";
  return "Every expert started here. Use Practice mode at 0.9× and try again. You've got this. 🌱";
}

function showResults(result) {
  $("#e-live").hidden = true;
  $("#e-results").hidden = false;
  $("#e-score").textContent = `${result.score} / ${result.total}`;
  $("#e-band").textContent = result.band != null ? `Estimated band ${result.band.toFixed(1)}` :
    `${pct(result.score, result.total)}%`;
  $("#e-cheer").textContent = cheer(result.score / Math.max(result.total, 1));
  const parts = $("#e-parts-score");
  parts.replaceChildren();
  const byPart = Object.entries(result.by_part || {});
  if (byPart.length > 1) for (const [n, [r, t]] of byPart) parts.append(el("span", { className: "chip" }, `Part ${n} `, el("b", { textContent: `${r}/${t}` })));

  const table = $("#e-table");
  table.replaceChildren(el("tr", {}, ...["Q", "Type", "Your answer", "Correct", ""].map((h) => el("th", { textContent: h }))));
  for (const [n, r] of Object.entries(result.results)) {
    table.append(el("tr", { className: r.correct ? "" : "miss" },
      el("td", { textContent: n }),
      el("td", { className: "muted small", textContent: TYPE_LABELS[r.type] || "" }),
      el("td", {}, r.given || "—", r.reason ? el("div", { className: "bad small", textContent: r.reason }) : null),
      el("td", { textContent: r.key.replaceAll("|", " / ") }),
      el("td", { className: r.correct ? "ok" : "bad", textContent: r.correct ? "✓" : "✗" })));
  }
  transcriptItems($("#e-transcript"), state.test, { clickable: false });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* ================================ progress ================================ */
async function loadHistory() {
  const { history } = await api("/api/history");
  state.history = history;
  const table = $("#h-table"), chart = $("#h-chart"), types = $("#h-types"), partsBox = $("#h-parts");
  table.replaceChildren(); chart.replaceChildren(); types.replaceChildren(); partsBox.replaceChildren();
  if (!history.length) {
    $("#h-summary").textContent = "No exams taken yet. Your first score will show up here. Day one starts now.";
    chart.hidden = true;
    types.append(el("tr", {}, el("td", { className: "muted", textContent: "Take an exam on any task page to see your accuracy by question type." })));
    return;
  }
  chart.hidden = false;
  const ratio = (h) => h.score / Math.max(h.total, 1);
  const recent = history.slice(-5);
  const avg = recent.reduce((n, h) => n + ratio(h), 0) / recent.length;
  const days = new Set(history.map((h) => h.date.slice(0, 10))).size;
  const bands = history.filter((h) => h.band != null);
  $("#h-summary").textContent =
    `${history.length} exam${history.length === 1 ? "" : "s"} over ${days} day${days === 1 ? "" : "s"} · ` +
    `last-5 average ${Math.round(avg * 100)}%` + (bands.length ? ` · latest full-test band ${bands.at(-1).band.toFixed(1)}` : "");

  // Per Part (from part tests and full tests alike).
  for (const n of ["1", "2", "3", "4"]) {
    let r = 0, t = 0;
    for (const h of history) if (h.by_part?.[n]) { r += h.by_part[n][0]; t += h.by_part[n][1]; }
    partsBox.append(el("a", { className: "stat", href: `#part${n}` },
      el("span", { textContent: `Part ${n}` }), el("b", { textContent: t ? `${pct(r, t)}%` : "—" }),
      el("small", { textContent: t ? `${r}/${t} correct` : "not practised yet" })));
  }

  // Per question type, weakest first.
  const totals = {};
  for (const h of history) for (const [k, [r, t]] of Object.entries(h.by_type || {})) {
    totals[k] ??= [0, 0];
    totals[k][0] += r;
    totals[k][1] += t;
  }
  const rows = Object.entries(totals).sort((a, b) => a[1][0] / a[1][1] - b[1][0] / b[1][1]);
  types.append(el("tr", {}, ...["Question type", "Accuracy", "", ""].map((x) => el("th", { textContent: x }))));
  rows.forEach(([type, [r, t]], i) => {
    const drill = DRILL[type];
    const bar = el("div", { className: "bar-track" }, el("div", { className: "bar-fill", style: `width:${pct(r, t)}%` }));
    types.append(el("tr", { className: i < 3 && pct(r, t) < 90 ? "weak" : "" },
      el("td", { textContent: TYPE_LABELS[type] || type }),
      el("td", {}, bar, el("small", { className: "muted", textContent: `${pct(r, t)}% · ${r}/${t}` })),
      el("td", { textContent: i < 3 && pct(r, t) < 90 ? "🎯" : "" }),
      el("td", {}, drill ? el("button", { className: "ghost small-btn", textContent: "Drill this", onclick: () => drillType(drill, type) }) : "")));
  });

  for (const h of history.slice(-40)) {
    chart.append(el("div", { className: `col ${h.kind || ""}`, style: `height:${Math.max(3, ratio(h) * 100)}%`,
      dataset: { tip: `${h.date} · ${kindLabel(h.kind)} · ${h.score}/${h.total}` } }));
  }
  table.append(el("tr", {}, ...["Date", "Task", "Recording", "Score", "Band"].map((x) => el("th", { textContent: x }))));
  for (const h of [...history].reverse().slice(0, 50)) {
    table.append(el("tr", {},
      el("td", { textContent: h.date }), el("td", { textContent: kindLabel(h.kind) }), el("td", { textContent: h.title }),
      el("td", { textContent: `${h.score} / ${h.total}` }),
      el("td", { textContent: h.band != null ? h.band.toFixed(1) : "—" })));
  }
}

function drillType(task, type) {
  const saved = store.get(`prompt:${task}`, {});
  const focusIds = (state.tasks?.tasks[task]?.focus || []).map((f) => f.id);
  store.set(`prompt:${task}`, { ...saved, focus: focusIds.includes(type) ? type : "mix", topic: "" });
  delete state.prompts[task];
  go(task);
  toast(`${kindLabel(task)} prompt set to drill: ${TYPE_LABELS[type] || type}`, 3000);
}

/* ================================ boot ================================ */
(async function boot() {
  $("#p-speed").value = store.get("speed", "1");
  try { await loadStatus(); } catch { toast("Can't reach the local server. Is run.bat still open?", 6000); return; }
  try {
    state.tasks = await api("/api/tasks");
    $("#t-difficulty").replaceChildren(...state.tasks.difficulty.map((d) => el("option", { value: d.id, textContent: d.label })));
  } catch (err) { toast(err.message); }
  await Promise.all([loadLibrary(), loadTests(), api("/api/history").then((r) => (state.history = r.history))]);
  state.task = null;
  const last = store.get("test", null);
  if (last && state.tests.some((t) => t.id === last)) await openTest(last);
  else if (state.tests[0]) await openTest(state.tests[0].id);
  showRoute(location.hash.slice(1) || "home");
})();

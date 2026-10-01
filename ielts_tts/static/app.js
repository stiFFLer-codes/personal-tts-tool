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

const state = {
  ready: false,
  mp3: false,
  voices: [],
  parsed: null,          // last /api/parse result
  castChoice: {},        // user's voice picks, kept across re-parses by speaker name
  test: null,            // currently loaded recording (public meta)
  tests: [],
  examRunning: false,
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

function speakerColour(name, test = state.test) {
  if (name === NARRATOR) return "#6a7180";
  const order = test ? Object.keys(test.cast).filter((s) => s !== NARRATOR) : [];
  const i = order.indexOf(name);
  return SPEAKER_COLOURS[(i < 0 ? 0 : i) % SPEAKER_COLOURS.length];
}

/* ================================ tabs ================================ */
function showTab(name) {
  if (state.examRunning && name !== "exam") {
    if (!confirm("Leave the exam? The recording will stop and this attempt won't be marked.")) return;
    stopExam();
  }
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === `tab-${name}`));
  if (name !== "practice") practiceAudio.pause();
  if (name === "progress") loadHistory();
  if (name === "exam" && !state.examRunning) showExamIntro();
  store.set("tab", name);
}
$$(".tab").forEach((t) => t.addEventListener("click", () => showTab(t.dataset.tab)));
document.addEventListener("click", (e) => {
  const go = e.target.closest("[data-goto]");
  if (go) showTab(go.dataset.goto);
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

/* ================================ studio ================================ */
const scriptBox = $("#script");
let parseTimer;

scriptBox.addEventListener("input", () => {
  store.set("draft", scriptBox.value);
  clearTimeout(parseTimer);
  parseTimer = setTimeout(parseScript, 350);
});

async function parseScript() {
  const script = scriptBox.value;
  if (!script.trim()) {
    state.parsed = null;
    renderCast();
    return;
  }
  try {
    state.parsed = await api("/api/parse", { script });
    renderCast();
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

function renderCast() {
  const p = state.parsed;
  const cast = $("#cast"), stats = $("#stats"), warnings = $("#warnings");
  cast.replaceChildren(); stats.replaceChildren(); warnings.replaceChildren();
  $("#btn-generate").disabled = !p || !p.test.segments.some((s) => s.kind === "speech");
  if (!p) { $("#parsed-title").textContent = "Cast & generate"; return; }

  const t = p.test;
  $("#parsed-title").textContent = t.title;
  const speech = t.segments.filter((s) => s.kind === "speech");
  const pauses = t.segments.filter((s) => s.kind === "pause");
  const words = speech.reduce((n, s) => n + s.text.split(/\s+/).length, 0);
  const estimate = words / 2.6 + pauses.reduce((n, s) => n + s.seconds, 0);  // ~155 wpm
  const chip = (label, value) => el("span", { className: "chip" }, `${label} `, el("b", { textContent: value }));
  stats.append(
    chip("Speakers", t.speakers.length),
    chip("Lines", speech.length),
    chip("Pauses", pauses.length ? `${pauses.length} (${pauses.reduce((n, s) => n + s.seconds, 0)} s)` : 0),
    chip("Questions", t.question_numbers.length),
    chip("≈", fmt(estimate)),
  );

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
  for (const w of t.warnings) warnings.append(el("li", { textContent: w }));
}

function currentCast() {
  const p = state.parsed;
  const out = {};
  for (const row of $$("#cast .cast-row")) out[row.dataset.speaker] = row.querySelector("select").value;
  return Object.keys(out).length ? out : (p?.cast || {});
}

$("#btn-generate").addEventListener("click", async () => {
  const btn = $("#btn-generate");
  btn.disabled = true;
  $("#render-result").hidden = true;
  const bar = $("#progress");
  bar.hidden = false;
  setProgress(0, 0, "Starting…");
  try {
    const { job } = await api("/api/render", { script: scriptBox.value, cast: currentCast() });
    const result = await pollJob(job);
    setTest(result);
    showRenderResult(result);
    loadTests();
  } catch (err) {
    toast(err.message, 5000);
  } finally {
    bar.hidden = true;
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
    await new Promise((r) => setTimeout(r, 500));
  }
}

function showRenderResult(test) {
  $("#render-result").hidden = false;
  $("#result-text").textContent = `${test.title}: ${fmt(test.duration)} of audio ready`;
  const wav = $("#dl-wav");
  wav.href = `${test.audio}?download`;
  const mp3 = $("#dl-mp3");
  mp3.hidden = !state.mp3;
  mp3.href = `/api/export/${test.id}.mp3`;
}

$("#btn-clear").addEventListener("click", () => {
  if (scriptBox.value.trim() && !confirm("Clear the current script?")) return;
  scriptBox.value = "";
  store.set("draft", "");
  state.castChoice = {};
  parseScript();
  scriptBox.focus();
});

$("#btn-save").addEventListener("click", async () => {
  if (!scriptBox.value.trim()) return toast("Nothing to save yet.");
  try {
    const { file } = await api("/api/library", { script: scriptBox.value });
    toast(`Saved to library/${file}`);
    loadLibrary(file);
  } catch (err) { toast(err.message); }
});

async function loadLibrary(selected = "") {
  const { items } = await api("/api/library");
  const select = $("#library-select");
  select.replaceChildren(el("option", { value: "", textContent: `📚 Library (${items.length})…` }));
  for (const item of items) select.append(el("option", { value: item.file, textContent: item.title, selected: item.file === selected }));
}
$("#library-select").addEventListener("change", async (e) => {
  const file = e.target.value;
  if (!file) return;
  if (scriptBox.value.trim() && scriptBox.value !== store.get("loaded", "") &&
      !confirm("Replace the script in the editor?")) { e.target.value = ""; return; }
  const { script } = await api(`/api/library/${encodeURIComponent(file)}`);
  scriptBox.value = script;
  store.set("draft", script);
  store.set("loaded", script);
  state.castChoice = {};
  parseScript();
});

async function loadTests() {
  const { tests } = await api("/api/tests");
  state.tests = tests;
  const recent = $("#recent");
  recent.replaceChildren();
  if (!tests.length) recent.append(el("li", { className: "muted", textContent: "Nothing yet. Generate your first recording!" }));
  for (const t of tests.slice(0, 8)) {
    const li = el("li", {},
      el("span", { textContent: t.title }),
      el("span", { className: "meta", textContent: `${fmt(t.duration)} · ${t.questions} Q · ${t.voices} · ${t.created}` }));
    li.addEventListener("click", () => openTest(t.id, "practice"));
    recent.append(li);
  }
  for (const picker of $$(".test-picker")) {
    picker.replaceChildren(el("option", { value: "", textContent: "Choose a recording…" }));
    for (const t of tests) picker.append(el("option", { value: t.id, textContent: t.title, selected: t.id === state.test?.id }));
  }
}
document.addEventListener("change", (e) => {
  if (e.target.matches(".test-picker") && e.target.value) openTest(e.target.value);
});

async function openTest(id, tab) {
  try {
    setTest(await api(`/api/tests/${id}`));
    if (tab) showTab(tab);
    else if ($("#tab-exam").classList.contains("active")) showExamIntro();
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
// Turns the plain-text question paper into lines with answer boxes.
//   "Name: Clara 1 ________"  -> inline box for Q1
//   "7. Why did the man..."   -> box at the end of the line (MCQ letter)
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

  for (let line of (text || "").split("\n")) {
    // "22. ...the sleep 22 ________." -> drop the duplicate leading "22."
    const dup = line.match(/^\s*(\d{1,2})\s*[.)]\s+/);
    if (dup && new RegExp(`(?<!\\d)${dup[1]}\\s*(?:_{2,}|…+|\\.{4,})`).test(line.slice(dup[0].length))) line = line.slice(dup[0].length);
    const div = el("div", { className: "qline" });
    const trimmed = line.trim();
    if (/^questions?\s+\d/i.test(trimmed) || (trimmed.length > 3 && trimmed === trimmed.toUpperCase() && /[A-Z]/.test(trimmed))) div.classList.add("qhead");
    if (/^[A-H][.)]?\s+\S/.test(trimmed) && !/^[A-H][a-z]/.test(trimmed)) div.classList.add("qopt");

    // 1) numbered gaps anywhere in the line: "Name: Clara 1 ________"
    let last = 0, m;
    gap.lastIndex = 0;
    while ((m = gap.exec(line))) {
      const n = Number(m[1]);
      if (!numbers.includes(n) || placed.has(n)) continue;
      div.append(line.slice(last, m.index), label(n), input(n));
      last = m.index + m[0].length;
    }
    if (last) { div.append(line.slice(last)); container.append(div); continue; }

    // 2) "7. The tour starts at ______" or an MCQ stem "7. Why did...?" (box at the end)
    const lead = line.match(/^\s*(\d{1,2})\s*[.)]\s/);
    const n = lead ? Number(lead[1]) : null;
    if (n && numbers.includes(n) && !placed.has(n)) {
      const body = line.slice(lead[0].length);
      const blank = body.match(/_{2,}|…+/);
      div.append(label(n));
      if (blank) div.append(body.slice(0, blank.index), input(n), body.slice(blank.index + blank[0].length));
      else div.append(body, " ", input(n));
    } else {
      div.append(line || "\u00a0");
    }
    container.append(div);
  }

  const leftovers = numbers.filter((n) => !placed.has(n));
  if (leftovers.length) {
    const extra = el("div", { className: "extra-answers" }, el("div", { className: "qhead", textContent: "Answer sheet" }));
    for (const n of leftovers) extra.append(el("div", { className: "qline" }, label(n), input(n)));
    container.append(extra);
  }
}

const collectAnswers = (container) =>
  Object.fromEntries($$("input.ans", container).map((i) => [i.dataset.q, i.value]));

/* ================================ practice ================================ */
const practiceAudio = new Audio();
practiceAudio.preload = "auto";
let currentLine = -1;
let loopLine = false;

function speechLines(test = state.test) {
  return test ? test.timeline.filter((x) => x.kind === "speech") : [];
}

function transcriptItems(list, test, { clickable }) {
  list.replaceChildren();
  test.timeline.forEach((item, idx) => {
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
  if (hasQ) renderQuestions($("#p-questions"), test.questions, test.question_numbers);
  updateClock();
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
    $$("#p-transcript li").forEach((li) => li.classList.toggle("current", Number(li.dataset.idx) === idx));
    const cur = $(`#p-transcript li[data-idx="${idx}"]`);
    if (cur && !practiceAudio.paused) cur.scrollIntoView({ block: "nearest", behavior: "smooth" });
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
  $("#tab-practice").classList.toggle("blind", e.target.checked);
  $$("#p-transcript li.revealed").forEach((li) => li.classList.remove("revealed"));
});
$("#p-showq").addEventListener("change", (e) => {
  $("#p-questions-card").hidden = !e.target.checked || !state.test?.question_numbers.length;
});

document.addEventListener("keydown", (e) => {
  if (!$("#tab-practice").classList.contains("active") || !state.test) return;
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
const CHECK_SECONDS = 120;

function showExamIntro() {
  const t = state.test;
  $("#e-intro").hidden = false;
  $("#e-live").hidden = true;
  $("#e-results").hidden = true;
  if (!t) return;
  const n = t.question_numbers.length;
  $("#e-meta").textContent = `${fmt(t.duration)} of audio · ${n} question${n === 1 ? "" : "s"}`;
  $("#e-noanswers").hidden = n > 0;
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
  renderQuestions($("#e-questions"), t.questions || "(No question paper in this script, just listen.)", t.question_numbers);
  examAudio.src = t.audio;
  examAudio.currentTime = 0;
  examAudio.volume = Number($("#e-volume").value);
  examAudio.play().catch(() => toast("Click Start again: the browser blocked autoplay."));
  $("#e-questions input.ans")?.focus();
});

examAudio.addEventListener("timeupdate", () => {
  const d = examAudio.duration || state.test?.duration || 1;
  $("#e-track").style.width = `${(100 * examAudio.currentTime) / d}%`;
  $("#e-time").textContent = `${fmt(examAudio.currentTime)} / ${fmt(d)}`;
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
  } catch (err) {
    toast(err.message, 5000);
    showExamIntro();
  }
}

function cheer(pct) {
  if (pct === 1) return "Perfect score! Band 9 energy. Erasmus committee, take note. 🏆";
  if (pct >= 0.85) return "Excellent! That's band 8+ territory. Keep this streak alive. 🔥";
  if (pct >= 0.7) return "Solid work! Review the misses in Practice and you'll close the gap. 💪";
  if (pct >= 0.5) return "Good base. Replay the lines you missed with the transcript, then retake tomorrow. 📈";
  return "Every expert started here. Use Practice mode at 0.9× and try again. You've got this. 🌱";
}

function showResults(result) {
  $("#e-live").hidden = true;
  $("#e-results").hidden = false;
  $("#e-score").textContent = `${result.score} / ${result.total}`;
  $("#e-band").textContent = result.band != null ? `Estimated band ${result.band.toFixed(1)}` :
    `${Math.round((100 * result.score) / Math.max(result.total, 1))}%`;
  $("#e-cheer").textContent = cheer(result.score / Math.max(result.total, 1));

  const table = $("#e-table");
  table.replaceChildren(el("tr", {}, ...["Q", "Your answer", "Correct", ""].map((h) => el("th", { textContent: h }))));
  for (const [n, r] of Object.entries(result.results)) {
    table.append(el("tr", {},
      el("td", { textContent: n }),
      el("td", { textContent: r.given || "—" }),
      el("td", { textContent: r.key.replaceAll("|", " / ") }),
      el("td", { className: r.correct ? "ok" : "bad", textContent: r.correct ? "✓" : "✗" })));
  }
  transcriptItems($("#e-transcript"), state.test, { clickable: false });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* ================================ progress ================================ */
async function loadHistory() {
  const { history } = await api("/api/history");
  const table = $("#h-table"), chart = $("#h-chart");
  table.replaceChildren(); chart.replaceChildren();
  if (!history.length) {
    $("#h-summary").textContent = "No exams taken yet. Your first score will show up here. Day one starts now.";
    chart.hidden = true;
    return;
  }
  chart.hidden = false;
  const pct = (h) => h.score / Math.max(h.total, 1);
  const recent = history.slice(-5);
  const avg = recent.reduce((n, h) => n + pct(h), 0) / recent.length;
  const days = new Set(history.map((h) => h.date.slice(0, 10))).size;
  $("#h-summary").textContent =
    `${history.length} exam${history.length === 1 ? "" : "s"} over ${days} day${days === 1 ? "" : "s"} · ` +
    `last-5 average ${Math.round(avg * 100)}%`;
  for (const h of history.slice(-40)) {
    chart.append(el("div", { className: "col", style: `height:${Math.max(3, pct(h) * 100)}%`,
      dataset: { tip: `${h.date} · ${h.score}/${h.total}` } }));
  }
  table.append(el("tr", {}, ...["Date", "Recording", "Score", "Band"].map((x) => el("th", { textContent: x }))));
  for (const h of [...history].reverse()) {
    table.append(el("tr", {},
      el("td", { textContent: h.date }), el("td", { textContent: h.title }),
      el("td", { textContent: `${h.score} / ${h.total}` }),
      el("td", { textContent: h.band != null ? h.band.toFixed(1) : "—" })));
  }
}

/* ================================ boot ================================ */
(async function boot() {
  $("#p-speed").value = store.get("speed", "1");
  try { await loadStatus(); } catch { toast("Can't reach the local server. Is run.bat still open?", 6000); return; }
  await Promise.all([loadLibrary(), loadTests()]);
  const draft = store.get("draft", "");
  if (draft) scriptBox.value = draft;
  parseScript();
  const last = store.get("test", null);
  if (last && state.tests.some((t) => t.id === last)) await openTest(last);
  else if (state.tests[0]) await openTest(state.tests[0].id);
  showTab(store.get("tab", "studio"));
})();

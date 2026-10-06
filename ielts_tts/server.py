"""Tiny local web server (stdlib only). Serves the UI and a JSON API on 127.0.0.1."""

import json
import mimetypes
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import grader, prompt_builder, voices
from .engine import Engine, Jobs, ModelMissing, public_meta, _slug
from .parser import SET_TYPES, detect_task, parse_test
from .validator import TASK_PARTS, validate

ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).resolve().parent / "static"
LIBRARY = ROOT / "library"
RESULTS = ROOT / "results"
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".js": "text/javascript; charset=utf-8", ".wav": "audio/wav", ".mp3": "audio/mpeg",
         ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8"}


class App:
    def __init__(self, root: Path = ROOT):
        self.engine = Engine(root)
        self.jobs = Jobs(self.engine)

    def available_voices(self):
        if self.engine.ready:
            return {v["id"] for v in self.engine.voices()}
        return set(voices.FEMALE_ORDER + voices.MALE_ORDER + [voices.DEFAULT_NARRATOR])


def prepare(body: dict, available):
    """Parse + validate a pasted script for the page it was pasted on."""
    page = body.get("kind") or "custom"
    page = page if page in TASK_PARTS else "custom"
    test = parse_test(body.get("script", ""), page)
    detected = detect_task(test)
    if page == "custom":
        test.kind = detected
    checks = validate(test, page)
    cast = voices.assign(test.speakers, available, test.voice_overrides)
    return test, page, detected, checks, cast


def _history_path():
    return RESULTS / "history.json"


def load_history():
    path = _history_path()
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        server_version = "ListeningStudio/2.0"

        def log_message(self, fmt, *args):     # keep the console quiet except for errors
            if args and str(args[1])[:1] in "45":
                super().log_message(fmt, *args)

        # ---- helpers ---------------------------------------------------------
        def send_json(self, data, status=200):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def error(self, message, status=400):
            self.send_json({"error": message}, status)

        def read_json(self):
            length = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(length) or b"{}")

        def send_file(self, path: Path, download_name=None):
            if not path.is_file():
                return self.error("Not found", 404)
            size = path.stat().st_size
            # Explicit types: on Windows, mimetypes reads the registry, which can map .js/.css to text/plain.
            ctype = TYPES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            start, end, status = 0, size - 1, 200
            m = re.match(r"bytes=(\d*)-(\d*)$", self.headers.get("Range", ""))
            if m and (m.group(1) or m.group(2)):
                if m.group(1):
                    start = int(m.group(1))
                    end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
                else:                                   # bytes=-500 -> last 500 bytes
                    start = max(size - int(m.group(2)), 0)
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
                status = 206
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            if download_name:
                self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
            self.end_headers()
            try:
                with path.open("rb") as f:
                    f.seek(start)
                    remaining = end - start + 1
                    while remaining > 0:
                        chunk = f.read(min(1 << 16, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass                                    # browser seeked away; normal for audio

        # ---- routes ----------------------------------------------------------
        def do_GET(self):
            url = urlparse(self.path)
            path, query = unquote(url.path), parse_qs(url.query)
            try:
                if path in ("/", "/index.html"):
                    return self.send_file(STATIC / "index.html")
                if path.startswith("/static/"):
                    name = path[len("/static/"):]
                    parts = name.split("/")
                    if (not re.fullmatch(r"[\w.-]+(?:/[\w.-]+)?", name)
                            or any(part in (".", "..") for part in parts)):
                        return self.error("Not found", 404)
                    return self.send_file(STATIC / name)
                if path.startswith("/output/"):
                    name = path[len("/output/"):]
                    if not re.fullmatch(r"[\w.-]+\.(wav|mp3)", name):
                        return self.error("Not found", 404)
                    download = name if "download" in query else None
                    return self.send_file(app.engine.output_dir / name, download)
                if path == "/api/status":
                    return self.send_json({"ready": app.engine.ready,
                                           "model": app.engine.model_path.name if app.engine.model_path else None,
                                           "mp3": app.engine.mp3_available()})
                if path == "/api/voices":
                    return self.send_json({"voices": app.engine.voices(),
                                           "narrator": voices.DEFAULT_NARRATOR})
                if path == "/api/preview":
                    voice = (query.get("voice") or [""])[0]
                    if voice not in app.available_voices():
                        return self.error("Unknown voice")
                    return self.send_file(app.engine.preview(voice))
                if m := re.fullmatch(r"/api/jobs/(\w+)", path):
                    job = app.jobs.get(m.group(1))
                    return self.send_json(job) if job else self.error("No such job", 404)
                if path == "/api/tests":
                    tests, history = [], load_history()
                    for meta_path in sorted(app.engine.output_dir.glob("*.json"),
                                            key=lambda p: p.stat().st_mtime, reverse=True):
                        meta = json.loads(meta_path.read_text(encoding="utf-8"))
                        tests.append({"id": meta["id"], "title": meta["title"], "duration": meta["duration"],
                                      "created": meta["created"], "questions": len(meta["question_numbers"]),
                                      "kind": meta.get("kind", "custom"),
                                      "best": max((h["score"] for h in history if h.get("id") == meta["id"]),
                                                  default=None),
                                      "voices": " / ".join(v.split("_", 1)[-1].capitalize()
                                                           for k, v in meta["cast"].items() if k != "Narrator")})
                    return self.send_json({"tests": tests})
                if m := re.fullmatch(r"/api/tests/([a-z0-9-]+)", path):
                    meta = app.engine.load_meta(m.group(1))
                    return self.send_json(public_meta(meta)) if meta else self.error("No such test", 404)
                if m := re.fullmatch(r"/api/export/([a-z0-9-]+)\.mp3", path):
                    if not app.engine.mp3_available():
                        return self.error("MP3 export needs ffmpeg on your PATH. WAV always works.")
                    if not app.engine.load_meta(m.group(1)):
                        return self.error("No such test", 404)
                    return self.send_file(app.engine.export_mp3(m.group(1)), f"{m.group(1)}.mp3")
                if path == "/api/library":
                    items = []
                    for f in sorted(LIBRARY.glob("*.txt")):
                        test = parse_test(f.read_text(encoding="utf-8"))
                        items.append({"file": f.name, "title": test.title, "kind": detect_task(test)})
                    return self.send_json({"items": items})
                if m := re.fullmatch(r"/api/library/([\w.-]+\.txt)", path):
                    f = LIBRARY / m.group(1)
                    if not f.is_file():
                        return self.error("Not found", 404)
                    return self.send_json({"file": f.name, "script": f.read_text(encoding="utf-8")})
                if path == "/api/tasks":
                    return self.send_json({"tasks": list(prompt_builder.TASKS), "types": SET_TYPES})
                if path == "/api/prompt":
                    task = (query.get("task") or [""])[0]
                    if task not in prompt_builder.TASKS:
                        return self.error("Unknown task")
                    return self.send_json(prompt_builder.build(task, note=(query.get("note") or [""])[0]))
                if path == "/api/history":
                    return self.send_json({"history": load_history()})
                return self.error("Not found", 404)
            except ModelMissing as exc:
                return self.error(str(exc), 503)

        def do_POST(self):
            path = urlparse(self.path).path
            try:
                body = self.read_json()
            except (ValueError, json.JSONDecodeError):
                return self.error("Invalid JSON")
            try:
                if path == "/api/parse":
                    test, page, detected, checks, cast = prepare(body, app.available_voices())
                    return self.send_json({"test": test.to_dict(), "cast": cast, "checks": checks,
                                           "detected": detected})
                if path == "/api/render":
                    available = app.available_voices()
                    test, page, detected, checks, cast = prepare(body, available)
                    if not any(s.kind == "speech" for s in test.segments):
                        return self.error("Nothing to read. Paste a script first.")
                    if page != "custom" and not checks["ok"]:
                        return self.error("The script doesn't match the exam format yet. Fix the ❌ items "
                                          "in the checklist (or ask Claude to fix them) and try again.")
                    cast.update({k: v for k, v in (body.get("cast") or {}).items() if v in available})
                    app.engine.kokoro()             # fail fast with a friendly message if no model
                    return self.send_json({"job": app.jobs.start(test, cast)})
                if path == "/api/library":
                    script = body.get("script", "")
                    if not script.strip():
                        return self.error("Nothing to save.")
                    name = body.get("file") or f"{_slug(parse_test(script).title)}.txt"
                    if not re.fullmatch(r"[\w.-]+\.txt", name):
                        return self.error("Bad file name")
                    LIBRARY.mkdir(exist_ok=True)
                    (LIBRARY / name).write_text(script, encoding="utf-8")
                    return self.send_json({"file": name})
                if path == "/api/grade":
                    meta = app.engine.load_meta(body.get("id", ""))
                    if not meta:
                        return self.error("No such test", 404)
                    if not meta.get("answers"):
                        return self.error("This test has no === ANSWERS === section to mark against.")
                    result = grader.grade(meta["answers"], body.get("answers") or {},
                                          meta.get("answer_groups"), meta.get("sets"))
                    history = load_history()
                    history.append({"date": time.strftime("%Y-%m-%d %H:%M"), "id": meta["id"],
                                    "title": meta["title"], "kind": meta.get("kind", "custom"),
                                    "score": result["score"], "total": result["total"], "band": result["band"],
                                    "by_type": result["by_type"], "by_part": result["by_part"]})
                    RESULTS.mkdir(exist_ok=True)
                    _history_path().write_text(json.dumps(history, indent=1, ensure_ascii=False),
                                               encoding="utf-8")
                    return self.send_json(result)
                return self.error("Not found", 404)
            except ModelMissing as exc:
                return self.error(str(exc), 503)

    return Handler


def serve(port=8765, host="127.0.0.1"):
    app = App()
    server = ThreadingHTTPServer((host, port), make_handler(app))
    return server, app

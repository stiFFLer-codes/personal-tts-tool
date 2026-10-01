"""Kokoro wrapper: synthesise lines (with a disk cache) and stitch a full test."""

import hashlib
import json
import re
import shutil
import subprocess
import threading
import time
import uuid
import wave
from pathlib import Path

import numpy as np

from . import normalize
from .parser import NARRATOR, Test
from .voices import english_voices, lang_for

SAMPLE_RATE = 24000
MODEL_FILES = {"full": "kokoro-v1.0.onnx", "small": "kokoro-v1.0.int8.onnx"}
VOICES_FILE = "voices-v1.0.bin"

# Silence (seconds) stitched between lines. Kokoro trims each clip, so these are the real gaps.
LEAD_IN = 0.6
TAIL = 1.0
GAP_NEW_SPEAKER = 0.45
GAP_SAME_SPEAKER = 0.3
GAP_AROUND_NARRATOR = 0.9
GAP_LETTER = 0.22               # between letters when spelling "W - H - I - T..."
GAP_PART = 0.25                 # between a spelled word and the rest of the line


class ModelMissing(RuntimeError):
    pass


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "test"


def _silence(seconds: float) -> np.ndarray:
    return np.zeros(int(round(seconds * SAMPLE_RATE)), dtype=np.float32)


def _trim(samples: np.ndarray, pad: float = 0.03) -> np.ndarray:
    """Cut leading/trailing near-silence so letter gaps are exactly what we ask for."""
    frame = int(0.01 * SAMPLE_RATE)
    n = len(samples) // frame
    if n == 0:
        return samples
    energy = np.sqrt((samples[: n * frame].reshape(n, frame) ** 2).mean(axis=1))
    loud = np.where(energy > energy.max() * 0.03)[0]
    if not len(loud):
        return samples
    margin = int(pad * SAMPLE_RATE)
    return samples[max(loud[0] * frame - margin, 0): min((loud[-1] + 1) * frame + margin, len(samples))]


def write_wav(path: Path, samples: np.ndarray):
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())


class Engine:
    def __init__(self, root: Path):
        self.models_dir = root / "models"
        self.cache_dir = root / "cache"
        self.output_dir = root / "output"
        self._kokoro = None
        self._load_lock = threading.Lock()
        self._synth_lock = threading.Lock()

    # ---- model -------------------------------------------------------------
    @property
    def model_path(self):
        for key in ("full", "small"):
            path = self.models_dir / MODEL_FILES[key]
            if path.exists():
                return path
        return None

    @property
    def ready(self) -> bool:
        return self.model_path is not None and (self.models_dir / VOICES_FILE).exists()

    def kokoro(self):
        with self._load_lock:
            if self._kokoro is None:
                if not self.ready:
                    raise ModelMissing(
                        "Voice model not found. Run setup.bat (or: python -m ielts_tts.download_models).")
                from kokoro_onnx import Kokoro
                self._kokoro = Kokoro(str(self.model_path), str(self.models_dir / VOICES_FILE))
            return self._kokoro

    def voices(self) -> list:
        return english_voices(self.kokoro().get_voices())

    # ---- synthesis ---------------------------------------------------------
    def _clip(self, speech: str, voice: str) -> np.ndarray:
        """Synthesise one piece of already-normalised text, cached on disk."""
        key = hashlib.sha1(f"{self.model_path.name}|{voice}|{speech}".encode()).hexdigest()
        cached = self.cache_dir / f"{key}.npy"
        if cached.exists():
            return np.load(cached)
        kokoro = self.kokoro()
        with self._synth_lock:
            samples, _ = kokoro.create(speech, voice=voice, lang=lang_for(voice))
        samples = samples.astype(np.float32)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        np.save(cached, samples)
        return samples

    def synth(self, text: str, voice: str) -> np.ndarray:
        """One script line -> audio. Spelled words are said letter by letter with real gaps."""
        pieces = []
        for kind, value in normalize.speech_parts(text):
            if pieces:
                pieces.append(_silence(GAP_PART))
            if kind == "text":
                pieces.append(self._clip(value, voice))
                continue
            for i, letter in enumerate(value):
                if i:
                    pieces.append(_silence(GAP_LETTER))
                ending = "." if i == len(value) - 1 else ","
                pieces.append(_trim(self._clip(letter + ending, voice)))
        return np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)

    def preview(self, voice: str) -> Path:
        name = voice.split("_", 1)[-1].capitalize()
        audio = self.synth(f"Hello, I'm {name}. You will hear a conversation between two people.", voice)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"preview-{voice}.wav"
        if not path.exists():
            write_wav(path, audio)
        return path

    # ---- full test ---------------------------------------------------------
    def test_id(self, test: Test, cast: dict) -> str:
        fingerprint = json.dumps([test.title, [(s.kind, s.speaker, s.text, s.seconds) for s in test.segments],
                                  cast, self.model_path.name if self.model_path else ""])
        return f"{_slug(test.title)}-{hashlib.sha1(fingerprint.encode()).hexdigest()[:8]}"

    def render(self, test: Test, cast: dict, progress=lambda done, total: None) -> dict:
        test_id = self.test_id(test, cast)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        meta_path = self.output_dir / f"{test_id}.json"
        if meta_path.exists() and (self.output_dir / f"{test_id}.wav").exists():
            # Same audio; the question paper or answer key may have been edited since.
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta.update(title=test.title, questions=test.questions, question_numbers=test.question_numbers,
                        answers=test.answers, answer_groups=test.answer_groups)
            meta_path.write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
            return meta

        speech_total = sum(1 for s in test.segments if s.kind == "speech")
        pieces, timeline, cursor, done, previous = [_silence(LEAD_IN)], [], LEAD_IN, 0, None

        for index, seg in enumerate(test.segments):
            if seg.kind == "pause":
                pieces.append(_silence(seg.seconds))
                timeline.append({"i": index, "kind": "pause", "speaker": "", "text": seg.text,
                                 "seconds": seg.seconds, "start": round(cursor, 3),
                                 "end": round(cursor + seg.seconds, 3), "line": seg.line})
                cursor += seg.seconds
                previous = None
                continue

            if previous is not None:
                if NARRATOR in (previous, seg.speaker) and previous != seg.speaker:
                    gap = GAP_AROUND_NARRATOR
                else:
                    gap = GAP_SAME_SPEAKER if previous == seg.speaker else GAP_NEW_SPEAKER
                pieces.append(_silence(gap))
                cursor += gap

            audio = self.synth(seg.text, cast.get(seg.speaker) or cast[NARRATOR])
            pieces.append(audio)
            length = len(audio) / SAMPLE_RATE
            timeline.append({"i": index, "kind": "speech", "speaker": seg.speaker, "text": seg.text,
                             "start": round(cursor, 3), "end": round(cursor + length, 3), "line": seg.line})
            cursor += length
            previous = seg.speaker
            done += 1
            progress(done, speech_total)

        pieces.append(_silence(TAIL))
        samples = np.concatenate(pieces)
        write_wav(self.output_dir / f"{test_id}.wav", samples)

        meta = {
            "id": test_id,
            "title": test.title,
            "audio": f"/output/{test_id}.wav",
            "duration": round(len(samples) / SAMPLE_RATE, 2),
            "cast": cast,
            "timeline": timeline,
            "questions": test.questions,
            "question_numbers": test.question_numbers,
            "answers": test.answers,
            "answer_groups": test.answer_groups,
            "created": time.strftime("%Y-%m-%d %H:%M"),
        }
        meta_path.write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
        return meta

    def load_meta(self, test_id: str):
        if not re.fullmatch(r"[a-z0-9-]+", test_id):
            return None
        path = self.output_dir / f"{test_id}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    @staticmethod
    def mp3_available() -> bool:
        return shutil.which("ffmpeg") is not None

    def export_mp3(self, test_id: str) -> Path:
        wav = self.output_dir / f"{test_id}.wav"
        mp3 = wav.with_suffix(".mp3")
        if not mp3.exists():
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                            "-codec:a", "libmp3lame", "-q:a", "4", str(mp3)], check=True)
        return mp3


def public_meta(meta: dict) -> dict:
    """What the browser gets: everything except the answer key (that stays for grading)."""
    return {k: v for k, v in meta.items() if k != "answers"}


class Jobs:
    """Render tests on a background thread so the UI can show progress."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self._jobs = {}
        self._lock = threading.Lock()

    def start(self, test: Test, cast: dict) -> str:
        job_id = uuid.uuid4().hex[:12]
        self._jobs[job_id] = {"state": "running", "done": 0, "total": 0, "error": None, "result": None}

        def progress(done, total):
            self._jobs[job_id].update(done=done, total=total)

        def run():
            try:
                with self._lock:      # one render at a time; the CPU is the bottleneck anyway
                    meta = self.engine.render(test, cast, progress)
                public = public_meta(meta)
                self._jobs[job_id].update(state="done", result=public)
            except Exception as exc:  # surfaced in the UI
                self._jobs[job_id].update(state="error", error=str(exc))

        threading.Thread(target=run, daemon=True).start()
        return job_id

    def get(self, job_id: str):
        return self._jobs.get(job_id)

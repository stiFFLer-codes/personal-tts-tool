"""Nothing the learner sees may mention the exam's name (personal preference)."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "ielts_tts" / "static"
NAME = re.compile(r"ielts", re.I)


class Branding(unittest.TestCase):
    def test_web_ui_files(self):
        for name in ("index.html", "app.js", "style.css"):
            text = (STATIC / name).read_text(encoding="utf-8")
            self.assertIsNone(NAME.search(text), f"{name} mentions the exam name")

    def test_console_windows(self):
        for name in ("setup.bat", "run.bat"):
            for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
                if re.match(r"\s*(echo|title)\b", line, re.I):
                    self.assertIsNone(NAME.search(line), f"{name}: {line.strip()}")

    def test_console_and_error_messages(self):
        sources = {p: p.read_text(encoding="utf-8") for p in (ROOT / "ielts_tts").glob("*.py")}
        for path, text in sources.items():
            for literal in re.findall(r"print\((f?\"[^\"]*\")", text) + re.findall(r"ModelMissing\(\s*(\"[^\"]*\")", text):
                self.assertIsNone(NAME.search(literal), f"{path.name}: {literal}")

    def test_server_header(self):
        text = (ROOT / "ielts_tts" / "server.py").read_text(encoding="utf-8")
        version = re.search(r'server_version = "([^"]+)"', text).group(1)
        self.assertIsNone(NAME.search(version))


if __name__ == "__main__":
    unittest.main()

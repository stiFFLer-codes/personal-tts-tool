"""Download the Kokoro voice model (one time). Stdlib only.

    python -m ielts_tts.download_models          # full model, ~325 MB (best quality, fastest on most CPUs)
    python -m ielts_tts.download_models --small  # int8 model, ~92 MB (smaller, but slower on many CPUs)
"""

import argparse
import sys
import urllib.request
from pathlib import Path

from .engine import MODEL_FILES, VOICES_FILE

BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


def download(name: str):
    target = MODELS_DIR / name
    if target.exists() and target.stat().st_size > 1_000_000:
        print(f"  [ok] {name} already downloaded")
        return
    MODELS_DIR.mkdir(exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    print(f"  downloading {name}")
    with urllib.request.urlopen(BASE + name) as response, partial.open("wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while chunk := response.read(1 << 20):
            out.write(chunk)
            done += len(chunk)
            if total:
                pct = done * 100 // total
                bar = "#" * (pct // 4)
                sys.stdout.write(f"\r    [{bar:<25}] {pct:3d}%  {done >> 20}/{total >> 20} MB")
                sys.stdout.flush()
    if total and done != total:
        partial.unlink(missing_ok=True)
        raise SystemExit(f"\n  Download of {name} was incomplete. Please run this again.")
    partial.replace(target)
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--small", action="store_true", help="download the smaller int8 model instead")
    args = ap.parse_args()
    print("Downloading the Kokoro voice model into", MODELS_DIR)
    download(MODEL_FILES["small" if args.small else "full"])
    download(VOICES_FILE)
    print("Done. Start the app with run.bat")


if __name__ == "__main__":
    main()

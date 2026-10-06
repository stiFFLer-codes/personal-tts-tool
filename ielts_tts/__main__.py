"""python -m ielts_tts [--port 8765] [--no-browser]"""

import argparse
import threading
import webbrowser

from .server import serve


def main():
    ap = argparse.ArgumentParser(prog="run.bat", description="Listening Studio")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true", help="don't open the browser automatically")
    args = ap.parse_args()

    url = f"http://127.0.0.1:{args.port}/"
    try:
        server, app = serve(args.port)
    except OSError:
        print(f"\n  Port {args.port} is busy. The studio is probably already running: {url}")
        print("  (or start it on another port: run.bat --port 8766)\n")
        if not args.no_browser:
            webbrowser.open(url)
        return
    print(f"\n  Listening Studio is running at {url}")
    if not app.engine.ready:
        print("  ! Voice model missing. Run setup.bat once, then start again.")
    print("  Press Ctrl+C to stop.\n")
    if not args.no_browser:
        threading.Timer(0.8, webbrowser.open, [url]).start()
    # Load the model in the background so the first "Generate" is quick.
    if app.engine.ready:
        threading.Thread(target=app.engine.kokoro, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Studio closed. See you at the next session.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

"""Run with `conda run -n Vyoma python start_local.py`; Ctrl-C stops both servers."""
from pathlib import Path
import os
import signal
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
runtime = ROOT / ".runtime"
runtime.mkdir(exist_ok=True)
env = os.environ.copy()
env["PATH"] = "/opt/homebrew/bin:" + env.get("PATH", "")
env["SUSHROTA_MODEL_PATH"] = str(ROOT / "models/sushrota/sushrota_sanskrit_asr_v5.nemo")
env["SUSHROTA_API_URL"] = "http://127.0.0.1:8001"
env["VAGDHENU_API_URL"] = "http://127.0.0.1:8001"
env["VAGDHENU_ALLOW_GRADIO_FALLBACK"] = "false"
env["PYTHONUNBUFFERED"] = "1"
env["TOKENIZERS_PARALLELISM"] = "false"
children = []


def cleanup():
    for child in children:
        if child.poll() is None:
            child.terminate()
    for child in children:
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()


def stop(*_):
    raise SystemExit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        with (runtime / "speech.log").open("a") as log:
            speech = subprocess.Popen(
                [str(ROOT / ".speech-env/bin/python"), "-m", "uvicorn",
                 "local_speech_server:app", "--host", "127.0.0.1", "--port", "8001"],
                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
            )
        children.append(speech)
        for _ in range(60):
            if speech.poll() is not None:
                raise RuntimeError("Speech service failed; see .runtime/speech.log")
            try:
                with urllib.request.urlopen("http://127.0.0.1:8001/health", timeout=1):
                    break
            except OSError:
                time.sleep(1)
        else:
            raise RuntimeError("Speech service did not become ready")
        children.append(subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "streamlit_antyakshari_game.py",
             "--server.address", "127.0.0.1", "--server.port", "8501", "--server.headless", "true"],
            cwd=ROOT, env=env,
        ))
        print("Game: http://localhost:8501 | Speech log: .runtime/speech.log", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(1)
        raise RuntimeError("A server stopped; see terminal output and .runtime/speech.log")
    finally:
        cleanup()

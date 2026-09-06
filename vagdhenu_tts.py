"""Vāgdhenu TTS client with local REST and Hugging Face Space backends."""

from __future__ import annotations

import base64
import os
import shutil
from pathlib import Path
from typing import Any

import requests

try:
    from gradio_client import Client
except ImportError:
    Client = None


def _setting(name: str, default: str = "") -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return default.strip()


API_URL = _setting("VAGDHENU_API_URL")
API_KEY = _setting("VAGDHENU_API_KEY")
SPACE_ID = _setting("VAGDHENU_SPACE_ID", "prathoshap/vagdhenu-demo")
HF_TOKEN = _setting("HF_TOKEN")
ALLOW_GRADIO_FALLBACK = _setting(
    "VAGDHENU_ALLOW_GRADIO_FALLBACK", "true"
).lower() not in {"0", "false", "no", "off"}

API_NAME = "/synthesize"
METER = "__auto__"
SEED = 60

_client = None
_last_error = ""
_last_backend = ""


def get_last_tts_error() -> str:
    return _last_error


def tts_backend_name() -> str:
    if _last_backend:
        return _last_backend
    if API_URL:
        return "private Vāgdhenu server"
    if ALLOW_GRADIO_FALLBACK and Client is not None and SPACE_ID:
        return "Vāgdhenu ZeroGPU fallback"
    return "Vāgdhenu unavailable"


def tts_available() -> bool:
    return bool(
        API_URL
        or (ALLOW_GRADIO_FALLBACK and Client is not None and SPACE_ID)
    )


def _set_backend(name: str) -> None:
    global _last_backend
    _last_backend = name


def _set_error(message: str) -> None:
    global _last_error
    _last_error = message
    if message:
        print(f"Vāgdhenu TTS: {message}", flush=True)


def _synthesize_url() -> str:
    base = API_URL.rstrip("/")
    return base if base.endswith("/synthesize") else base + "/synthesize"


def _save_audio_response(response: requests.Response, output_path: str) -> str:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if "application/json" not in response.headers.get("content-type", "").lower():
        destination.write_bytes(response.content)
        return str(destination)

    payload = response.json()
    for key in ("audio_base64", "audio_b64"):
        if payload.get(key):
            destination.write_bytes(base64.b64decode(payload[key]))
            return str(destination)
    for key in ("audio_url", "url"):
        if payload.get(key):
            audio_response = requests.get(payload[key], timeout=180)
            audio_response.raise_for_status()
            destination.write_bytes(audio_response.content)
            return str(destination)
    for key in ("path", "audio_path"):
        source = Path(payload.get(key, ""))
        if source.is_file():
            shutil.copyfile(source, destination)
            return str(destination)
    raise RuntimeError("The Vāgdhenu server returned no audio")


def _generate_from_local(text: str, output_path: str) -> str:
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    response = requests.post(
        _synthesize_url(),
        json={"text": text, "meter": METER, "seed": SEED},
        headers=headers,
        timeout=(15, 1200),
    )
    response.raise_for_status()
    result = _save_audio_response(response, output_path)
    _set_backend("private Vāgdhenu server")
    return result


def _get_gradio_client():
    global _client
    if _client is None:
        if Client is None:
            raise RuntimeError("gradio_client is not installed")
        kwargs = {"verbose": False}
        if HF_TOKEN:
            kwargs["hf_token"] = HF_TOKEN
        _client = Client(SPACE_ID, **kwargs)
    return _client


def _find_audio_path(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, Path)):
        return str(value)
    if isinstance(value, dict):
        for key in ("path", "name", "url"):
            found = _find_audio_path(value.get(key))
            if found:
                return found
    if isinstance(value, (list, tuple)):
        for item in value:
            found = _find_audio_path(item)
            if found:
                return found
    for attribute in ("path", "name"):
        if hasattr(value, attribute):
            found = _find_audio_path(getattr(value, attribute))
            if found:
                return found
    return ""


def _generate_from_gradio(text: str, output_path: str) -> str:
    result = _get_gradio_client().predict(
        text, METER, SEED, api_name=API_NAME
    )
    audio_result = result[0] if isinstance(result, (list, tuple)) and result else result
    source_path = _find_audio_path(audio_result)
    if not source_path:
        raise RuntimeError("The Vāgdhenu Space returned no audio")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source = Path(source_path)
    if source.is_file():
        shutil.copyfile(source, destination)
    elif source_path.startswith(("http://", "https://")):
        response = requests.get(source_path, timeout=180)
        response.raise_for_status()
        destination.write_bytes(response.content)
    else:
        raise FileNotFoundError(f"Returned audio was not found: {source_path}")
    _set_backend("Vāgdhenu ZeroGPU fallback")
    return str(destination)


def generate_speech(text: str, output_path: str = "computer_response.wav") -> str:
    """Generate speech without allowing a TTS failure to crash the game."""
    global _last_error, _last_backend
    _last_error = ""
    _last_backend = ""
    text = (text or "").strip()
    if not text:
        _set_error("No text was provided")
        return ""

    errors = []
    if API_URL:
        try:
            print("Vāgdhenu TTS: trying private server...", flush=True)
            return _generate_from_local(text, output_path)
        except Exception as exc:
            errors.append(f"private server: {type(exc).__name__}: {exc}")
    if ALLOW_GRADIO_FALLBACK and Client is not None and SPACE_ID:
        try:
            print("Vāgdhenu TTS: trying Gradio fallback...", flush=True)
            return _generate_from_gradio(text, output_path)
        except Exception as exc:
            errors.append(f"Gradio fallback: {type(exc).__name__}: {exc}")

    if not errors:
        errors.append("No Vāgdhenu backend is configured")
    _set_error(" | ".join(errors))
    return ""

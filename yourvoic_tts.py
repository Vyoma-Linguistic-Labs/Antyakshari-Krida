from __future__ import annotations

import base64
import os
import shutil
from pathlib import Path
from typing import Any

import requests

try:
    from gradio_client import Client
except Exception:
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


# ============================================================
# CONFIG
# ============================================================

# If this is set, Antyakshari will use YOUR Vāgdhenu server first.
#
# Example:
# VAGDHENU_API_URL = "https://your-vagdhenu-server.com"
#
# For local development on the same machine:
# VAGDHENU_API_URL = "http://127.0.0.1:8001"

VAGDHENU_API_URL = _setting(
    "VAGDHENU_API_URL",
    "",
)

# Optional protection for your private GPU server.
VAGDHENU_API_KEY = _setting(
    "VAGDHENU_API_KEY",
    "",
)


# ============================================================
# GRADIO FALLBACK
# ============================================================

# If your private/local server is not configured or fails,
# the public Vāgdhenu demo can still be used as fallback.

VAGDHENU_SPACE_ID = _setting(
    "VAGDHENU_SPACE_ID",
    "prathoshap/vagdhenu-demo",
)

HF_TOKEN = _setting(
    "HF_TOKEN",
    "",
)

ALLOW_GRADIO_FALLBACK = (
    _setting(
        "VAGDHENU_ALLOW_GRADIO_FALLBACK",
        "true",
    ).lower()
    not in {
        "0",
        "false",
        "no",
        "off",
    }
)


VAGDHENU_API_NAME = "/synthesize"

VAGDHENU_METER = "__auto__"

VAGDHENU_SEED = 60


_CLIENT = None

_LAST_ERROR = ""

_LAST_BACKEND = ""


# ============================================================
# HELPERS
# ============================================================

def _set_error(message: str) -> None:
    global _LAST_ERROR

    _LAST_ERROR = message

    if message:
        print(
            f"Vāgdhenu TTS: {message}",
            flush=True,
        )


def _set_backend(name: str) -> None:
    global _LAST_BACKEND

    _LAST_BACKEND = name


def get_last_tts_error() -> str:
    return _LAST_ERROR


def tts_backend_name() -> str:
    if _LAST_BACKEND:
        return _LAST_BACKEND

    if VAGDHENU_API_URL:
        return "private Vāgdhenu server"

    if (
        ALLOW_GRADIO_FALLBACK
        and Client is not None
        and VAGDHENU_SPACE_ID
    ):
        return "Vāgdhenu ZeroGPU fallback"

    return "Vāgdhenu unavailable"


def tts_available() -> bool:
    if VAGDHENU_API_URL:
        return True

    return bool(
        ALLOW_GRADIO_FALLBACK
        and Client is not None
        and VAGDHENU_SPACE_ID
    )


# ============================================================
# PRIVATE / LOCAL REST SERVER
# ============================================================

def _synthesize_url() -> str:
    base = VAGDHENU_API_URL.rstrip("/")

    if base.endswith("/synthesize"):
        return base

    return base + "/synthesize"


def _write_response_audio(
    response: requests.Response,
    output_path: str,
) -> str:

    destination = Path(output_path)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    content_type = (
        response.headers
        .get(
            "content-type",
            "",
        )
        .lower()
    )

    # Best case:
    # server directly returns WAV bytes.

    if "application/json" not in content_type:

        destination.write_bytes(
            response.content
        )

        return str(destination)


    # Compatibility:
    # also allow JSON responses.

    payload = response.json()


    for key in (
        "audio_base64",
        "audio_b64",
    ):

        encoded = payload.get(key)

        if encoded:

            destination.write_bytes(
                base64.b64decode(
                    encoded
                )
            )

            return str(destination)


    for key in (
        "audio_url",
        "url",
    ):

        url = payload.get(key)

        if url:

            audio_response = requests.get(
                url,
                timeout=180,
            )

            audio_response.raise_for_status()

            destination.write_bytes(
                audio_response.content
            )

            return str(destination)


    for key in (
        "path",
        "audio_path",
    ):

        local_path = payload.get(key)

        if (
            local_path
            and Path(local_path).exists()
        ):

            shutil.copyfile(
                local_path,
                destination,
            )

            return str(destination)


    raise RuntimeError(
        "The private Vāgdhenu server "
        "returned JSON but no audio."
    )


def _generate_from_local(
    text: str,
    output_path: str,
) -> str:

    headers = {}


    if VAGDHENU_API_KEY:

        headers[
            "X-API-Key"
        ] = VAGDHENU_API_KEY


    response = requests.post(

        _synthesize_url(),

        json={
            "text": text,
            "meter": VAGDHENU_METER,
            "seed": VAGDHENU_SEED,
        },

        headers=headers,

        timeout=(
            15,
            240,
        ),
    )


    response.raise_for_status()


    path = _write_response_audio(
        response,
        output_path,
    )


    _set_backend(
        "private Vāgdhenu server"
    )


    return path


# ============================================================
# PUBLIC GRADIO FALLBACK
# ============================================================

def _get_gradio_client():
    global _CLIENT


    if _CLIENT is not None:
        return _CLIENT


    if Client is None:

        raise RuntimeError(
            "gradio_client is not installed."
        )


    kwargs = {
        "verbose": False,
    }


    if HF_TOKEN:

        kwargs[
            "hf_token"
        ] = HF_TOKEN


    _CLIENT = Client(
        VAGDHENU_SPACE_ID,
        **kwargs,
    )


    return _CLIENT


def _find_audio_path(
    value: Any,
) -> str:

    if value is None:
        return ""


    if isinstance(
        value,
        (
            str,
            Path,
        ),
    ):

        return str(value)


    if isinstance(
        value,
        dict,
    ):

        for key in (
            "path",
            "name",
            "url",
        ):

            candidate = value.get(
                key
            )

            if candidate:

                found = _find_audio_path(
                    candidate
                )

                if found:
                    return found


    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):

        for item in value:

            found = _find_audio_path(
                item
            )

            if found:
                return found


    for attr in (
        "path",
        "name",
    ):

        if hasattr(
            value,
            attr,
        ):

            found = _find_audio_path(
                getattr(
                    value,
                    attr,
                )
            )

            if found:
                return found


    return ""


def _generate_from_gradio(
    text: str,
    output_path: str,
) -> str:

    client = _get_gradio_client()


    result = client.predict(

        text,

        VAGDHENU_METER,

        VAGDHENU_SEED,

        api_name=(
            VAGDHENU_API_NAME
        ),
    )


    audio_result = (

        result[0]

        if isinstance(
            result,
            (
                list,
                tuple,
            ),
        )
        and result

        else result
    )


    source_path = (
        _find_audio_path(
            audio_result
        )
    )


    if not source_path:

        raise RuntimeError(
            "The Vāgdhenu Space "
            "returned no audio file."
        )


    destination = Path(
        output_path
    )


    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    source = Path(
        source_path
    )


    if source.exists():

        shutil.copyfile(
            source,
            destination,
        )


        _set_backend(
            "Vāgdhenu ZeroGPU fallback"
        )


        return str(destination)


    if source_path.startswith(
        (
            "http://",
            "https://",
        )
    ):

        response = requests.get(
            source_path,
            timeout=180,
        )


        response.raise_for_status()


        destination.write_bytes(
            response.content
        )


        _set_backend(
            "Vāgdhenu ZeroGPU fallback"
        )


        return str(destination)


    raise RuntimeError(
        "Returned audio file "
        f"was not found: {source_path}"
    )


# ============================================================
# PUBLIC FUNCTION USED BY STREAMLIT
# ============================================================

def generate_speech(
    text: str,
    output_path: str = "computer_response.wav",
) -> str:

    """
    Generate Vāgdhenu audio.

    Priority:

    1. VAGDHENU_API_URL
       Your private/local REST server.

    2. Public Vāgdhenu Gradio Space
       only as fallback.

    A TTS error never crashes the game.
    """

    global _LAST_ERROR
    global _LAST_BACKEND


    _LAST_ERROR = ""

    _LAST_BACKEND = ""


    text = (
        text
        or ""
    ).strip()


    if not text:

        _set_error(
            "No text was provided."
        )

        return ""


    errors = []


    # --------------------------------------------------------
    # FIRST CHOICE: PRIVATE SERVER
    # --------------------------------------------------------

    if VAGDHENU_API_URL:

        try:

            print(
                "Vāgdhenu TTS: "
                "trying private server...",
                flush=True,
            )


            return _generate_from_local(
                text,
                output_path,
            )


        except Exception as exc:

            errors.append(

                "private server: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )


            print(
                "Vāgdhenu private "
                f"server failed: {exc}",
                flush=True,
            )


    # --------------------------------------------------------
    # FALLBACK: PUBLIC GRADIO
    # --------------------------------------------------------

    if (
        ALLOW_GRADIO_FALLBACK
        and Client is not None
        and VAGDHENU_SPACE_ID
    ):

        try:

            print(
                "Vāgdhenu TTS: "
                "trying Gradio fallback...",
                flush=True,
            )


            return _generate_from_gradio(
                text,
                output_path,
            )


        except Exception as exc:

            errors.append(

                "Gradio fallback: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )


    if not errors:

        errors.append(

            "No Vāgdhenu backend is configured. "
            "Set VAGDHENU_API_URL or enable "
            "the Gradio fallback."
        )


    _set_error(
        " | ".join(
            errors
        )
    )


    return ""

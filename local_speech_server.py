"""Local Su-shrota/Vagdhenu service; run with the project .speech-env Python."""
from pathlib import Path
import io
import os
import sys
import tempfile
import threading
from types import MethodType

ROOT = Path(__file__).resolve().parent
os.environ.pop("SUSHROTA_API_URL", None)
sys.path[:0] = [str(ROOT / "vendor/BigVGAN"), str(ROOT / "vendor/vagdhenu/src")]

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

app = FastAPI()
lock = threading.Lock()
renderer = None
torch.set_num_threads(int(os.environ.get("SPEECH_CPU_THREADS", "4")))


def select_tts_device() -> str:
    requested = os.environ.get("VAGDHENU_DEVICE", "auto").strip().lower()
    if requested == "auto":
        return "mps" if torch.backends.mps.is_available() else "cpu"
    if requested == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("VAGDHENU_DEVICE=mps was requested, but Metal is unavailable")
    if requested not in {"cpu", "mps"}:
        raise RuntimeError("VAGDHENU_DEVICE must be auto, cpu, or mps")
    return requested


tts_device = select_tts_device()


class Synthesis(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    meter: str = "__auto__"
    seed: int = 60


@app.get("/health")
def health():
    import sanskrit_asr
    return {"status": "ok", "asr_loaded": sanskrit_asr._MODEL is not None,
            "tts_loaded": renderer is not None, "tts_device": tts_device}


@app.post("/transcribe")
def transcribe(audio: UploadFile = File(...)):
    from sanskrit_asr import transcribe_audio
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = Path(tmp.name)
        tmp.write(audio.file.read())
    try:
        with lock:
            text = transcribe_audio(str(path))
        if not text:
            raise HTTPException(422, "No speech recognized; check the speech server log.")
        return {"text": text}
    finally:
        path.unlink(missing_ok=True)


@app.post("/synthesize")
def synthesize(request: Synthesis):
    global renderer
    from render_core import Renderer, detect_meter_key, FALLBACK_METER
    with lock:
        if renderer is None:
            renderer = Renderer(
                str(ROOT / "models/vagdhenu/voice_steer_ema_2026-06-17.pt"),
                str(ROOT / "models/vagdhenu/voc_bigvgan_EMA_2026-06-11.pth"),
                str(ROOT / "vendor/vagdhenu/src/reference_bank/bank.json"),
                device=tts_device,
                vocab_file=str(ROOT / "models/vagdhenu/vocab.txt"),
            )
            # Vocos and BigVGAN use operations unsupported by Apple MPS. Keep
            # those decoding stages on CPU while the large flow model uses Metal.
            renderer.cap.r = renderer.cap.r.to("cpu")

            def decode_vocos_on_cpu(cap, mel):
                cap.last = mel.detach().cpu().numpy()
                return cap.r.decode(mel.detach().to("cpu"))

            renderer.cap.decode = MethodType(decode_vocos_on_cpu, renderer.cap)

            if renderer.device == "mps":
                renderer.g = renderer.g.to("cpu")

                def decode_bigvgan_on_cpu(instance, mel):
                    tensor = torch.from_numpy(mel).to("cpu")
                    if tensor.dim() == 3 and tensor.shape[1] != 100 and tensor.shape[2] == 100:
                        tensor = tensor.transpose(1, 2)
                    with torch.no_grad():
                        audio = instance.g(tensor).squeeze().cpu().numpy()
                    return audio.astype(np.float32)

                renderer._bvgan = MethodType(decode_bigvgan_on_cpu, renderer)
        meter = request.meter
        if meter == "__auto__":
            meter = detect_meter_key(request.text) or FALLBACK_METER
        sr, audio = renderer.render_one(request.text, meter, seed=request.seed)
    output = io.BytesIO()
    sf.write(output, audio, sr, format="WAV")
    return Response(output.getvalue(), media_type="audio/wav")

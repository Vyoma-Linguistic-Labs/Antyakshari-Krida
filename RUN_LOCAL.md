# Run on this Mac

From the project folder:

```bash
conda activate Vyoma
python start_local.py
```

Open http://localhost:8501. Press Ctrl-C in the launcher terminal to stop both servers.
If a port is already occupied, stop the previous launcher before starting another.

The Streamlit game uses **Vyoma** (Python 3.13). Speech inference uses the
project's **.speech-env** (Python 3.10), because the older NeMo/IndicF5 dependencies
are incompatible with the main environment. Do not install the original
`requirements.txt` over Vyoma's existing packages.

The launcher connects both speech functions to http://127.0.0.1:8001 and disables
the public Hugging Face TTS fallback. Models run on CPU by default. Loading and
chant synthesis take longer than typed play; models remain loaded after first use.
Microphone access must be allowed in the browser. FFmpeg is installed via Homebrew.

## Files and diagnostics

- `models/sushrota/sushrota_sanskrit_asr_v5.nemo`: recognition checkpoint used by this game.
- `models/vagdhenu/voice_steer_ema_2026-06-17.pt`: Sanskrit chant voice.
- `models/vagdhenu/voc_bigvgan_EMA_2026-06-11.pth`: fine-tuned vocoder.
- `models/vagdhenu/vocab.txt`: tokenizer vocabulary.
- `vendor/vagdhenu`: inference code and reference audio bank.
- `vendor/IndicF5`: exact upstream inference commit `13f7c4d627cc10111aea8fe9c0039462cacacdc7`.
- `vendor/BigVGAN`: vocoder implementation.
- `vendor/NeMo`: AI4Bharat `nemo-v2` code.
- `.runtime/speech.log`: speech server output and errors.
- `http://127.0.0.1:8001/health`: service health and loaded-model flags.

The Vocos and NVIDIA base-vocoder resources are downloaded into the Hugging Face
cache on initial synthesis. The original `model_200_fixed.pth` is unused.
The older game README's YourVoic key and requirements filename are obsolete.

## Dependency notes

`requirements-speech-mac.txt` records the speech dependencies. NeMo was installed
separately with `--no-deps`, because its metadata requires Linux/CUDA Triton and
pins Hugging Face Hub to 0.23.2. This runtime uses Hub 0.23.5 to support BigVGAN
while retaining NeMo's legacy ModelFilter API. Consequently `pip check` reports
those two known NeMo metadata discrepancies. No Triton code is used for this
CPU CTC recognition path.

Local source changes explicitly restore ASR to CPU, route recognition to the
local service, and align Vocos with the selected TTS device.

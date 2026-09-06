# Sanskrit Antyakshari Krida

A Streamlit game for Sanskrit Antyākṣarī using Bhagavad Gita and Narayaneeyam
verse corpora. The player can recite or type a verse; the computer responds with
an unused verse beginning with the required akṣara.

## Features

- Su-śrotā Sanskrit speech recognition
- Vāgdhenu Sanskrit chant generation
- Strict final-akṣara and optional vowel-fallback rules
- Corpus-only and open-verse modes
- Three difficulty levels and a three-chance game loop
- No verse reuse and fuzzy corpus matching

## Run locally on macOS

The configured installation uses the `Vyoma` conda environment for Streamlit and
the project-local `.speech-env` for the older speech dependencies.

```bash
conda activate Vyoma
python start_local.py
```

Open <http://localhost:8501>. Press `Ctrl-C` in the launcher terminal to stop
both servers.

The launcher starts:

- the Streamlit game at `http://127.0.0.1:8501`
- the local speech API at `http://127.0.0.1:8001`

The speech service health endpoint is <http://127.0.0.1:8001/health>. Runtime
logs are written to `.runtime/speech.log`.

## Local models

The following ignored files are required:

- `models/sushrota/sushrota_sanskrit_asr_v5.nemo`
- `models/vagdhenu/voice_steer_ema_2026-06-17.pt`
- `models/vagdhenu/voc_bigvgan_EMA_2026-06-11.pth`
- `models/vagdhenu/vocab.txt`

Speech inference code is kept under the ignored `vendor/` directory: Vāgdhenu,
IndicF5, BigVGAN, and AI4Bharat NeMo. `requirements-speech-mac.txt` records the
Python 3.10 speech environment. NeMo is installed separately with `--no-deps`
because its metadata requires Linux/CUDA Triton, which is not used by the macOS
CPU CTC recognition path.

## Vāgdhenu performance on Apple Silicon

Vāgdhenu combines a 337M-parameter flow-matching model with 64 inference steps
and a BigVGAN vocoder. The speech server runs the large flow model on Metal
(`mps`) automatically on Apple Silicon. Vocos and BigVGAN stay on CPU because
their required operations are not supported by this PyTorch MPS build. The
hybrid path reduced a cold short-phrase test from about 96 seconds to 57 seconds.
Override the device for troubleshooting with:

```bash
VAGDHENU_DEVICE=cpu python start_local.py
```

The first request also loads several gigabytes of model weights. Later requests
reuse the loaded models and avoid that startup cost, but synthesis remains
computationally expensive.

## Project structure

- `streamlit_antyakshari_game.py` — game interface and turn flow
- `antyakshari_engine.py` — corpus loading, matching, and response strategy
- `sanskrit_asr.py` — Su-śrotā decoding and speech-service client
- `vagdhenu_tts.py` — Vāgdhenu client and optional public fallback
- `local_speech_server.py` — local ASR/TTS API
- `start_local.py` — launches the game and speech API together
- `BG_info.csv`, `Narayaneeyam_info.csv` — verse corpora
- `.streamlit/config.toml` — application theme

## Dependencies

`requirements.txt` contains the Streamlit-side dependencies.
`requirements-speech-mac.txt` contains the isolated Python 3.10 speech stack.

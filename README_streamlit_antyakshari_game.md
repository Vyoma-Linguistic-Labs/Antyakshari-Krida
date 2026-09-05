# Sanskrit Antyakshari Streamlit Game

## Run locally

For the configured Mac installation, start both the game and the local speech service:

```bash
conda activate Vyoma
python start_local.py
```

Open http://localhost:8501. See [RUN_LOCAL.md](RUN_LOCAL.md) for environment,
model, and troubleshooting details. The current app uses Su-śrotā and Vāgdhenu;
the older `model_200_fixed.pth` and YourVoic API key are not used.

## Features

- Rule Set `A`: strict `last_letter -> first_letter` matching.
- Rule Set `B`: strict first, with `swara_after_last` fallback only when strict has no move.
- Computer difficulty:
  - `Hard`: strongest continuation (best-path bias).
  - `Medium`: varied among strong valid options.
  - `Easy`: valid but less optimal continuation choices.
- Practice mode:
  - suggest up to 3 valid next verses when the player needs help.
- Computer recitation (TTS):
  - optional Vāgdhenu Sanskrit chant for computer verses.
  - the local launcher connects to the speech server on port 8001.
  - enable or disable `Use Vāgdhenu chant` in the sidebar.
- Verse source modes:
  - `Within Dataset Only`: player verse must match a corpus verse (with selected sensitivity).
  - `Allow Other Verses`: player may use non-dataset verses too.
- ASR typo/error handling in dataset mode:
  - closest matching verse is used as corrected text for continuation.
- No reuse:
  - dataset verses already used by player/computer are blocked.
  - custom non-dataset verses are also blocked from reuse.
- Turn-loss and game-over logic:
  - player can pass, but pass consumes a chance.
  - invalid/mistaken verses also consume a chance.
  - total `3` lost chances (pass + mistakes combined) ends the game.
- Continuation enforcement:
  - player verse must continue from the computer’s previous verse.
  - if no continuation path exists for current letter/rule set, player can start with any unused verse.
- Game log view:
  - latest turns are visible first, with two-line verse previews.
  - log area is scrollable to inspect older turns.
- Input modes:
  - `ASR Recording` (local Sanskrit STT model)
  - `Manual Text` (Devanagari verse input)
- Corpus selection:
  - Bhagavad Gita
  - Narayaneeyam
  - Combined

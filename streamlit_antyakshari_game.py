#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import html
import os
import tempfile
import uuid

import streamlit as st
from audiorecorder import audiorecorder

from antyakshari_engine import (
    DIFFICULTY_EASY,
    DIFFICULTY_HARD,
    DIFFICULTY_MEDIUM,
    RULE_SET_A,
    RULE_SET_B,
    AntyakshariEngine,
    available_corpus_files,
    infer_first_letter,
    infer_last_letter_and_swara,
    normalize_devanagari_text,
)

from sanskrit_asr import transcribe_audio

from yourvoic_tts import (
    generate_speech,
    get_last_tts_error,
    tts_available,
    tts_backend_name,
)

MAX_CHANCES = 3

VERSE_MODE_DATASET = "Within Dataset Only"
VERSE_MODE_OPEN = "Allow Other Verses"

RULE_LABELS = {
    "Strict — last अक्षर only": RULE_SET_A,
    "Swara Fallback — continue when strict path ends": RULE_SET_B,
}

DIFFICULTIES = [
    DIFFICULTY_HARD,
    DIFFICULTY_MEDIUM,
    DIFFICULTY_EASY,
]

VYOMA_LOGO_URL = (
    "https://avatars.githubusercontent.com/"
    "u/108797006?v=4"
)

VYOMA_REPO_URL = (
    "https://github.com/"
    "Vyoma-Linguistic-Labs/"
    "Antyakshari-Krida"
)

# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Sanskrit Antyakshari Krida",
    page_icon="🕉️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# CSS
# ============================================================

st.html(
    """
<style>
:root {
    --vyoma: #0B5FA5;
    --vyoma-dark: #083C6D;
    --gold: #E7B73C;
    --ink: #102A43;
    --muted: #66788A;
    --line: #DCE7F1;
    --soft: #F7F9FC;
}

.stApp {
    background: var(--soft);
}

.block-container {
    max-width: 1180px;
    padding-top: 4rem;
    padding-bottom: 2.5rem;
}

/* SIDEBAR */
[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #0C2744 0%,
        #163754 100%
    );
}

[data-testid="stSidebar"] * {
    color: #F7FAFC;
}

[data-testid="stSidebar"] small,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: #C8D6E5 !important;
}

[data-testid="stAppDeployButton"] {
    display: none;
}

[data-testid="stHeader"] {
    background: rgba(247,249,252,.92);
}

/* APP HEADER */
.app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    margin-bottom: 16px;
}

.app-title {
    color: var(--vyoma-dark);
    font-size: 1.65rem;
    line-height: 1.22;
    font-weight: 850;
}

.app-subtitle {
    margin-top: 3px;
    color: var(--muted);
    font-size: .88rem;
}

.brand-mark {
    display: flex;
    align-items: center;
    gap: 7px;
    background: white;
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 6px 11px 6px 7px;
    color: var(--muted);
    font-size: .74rem;
    white-space: nowrap;
}

.brand-mark img {
    width: 25px;
    height: 25px;
    border-radius: 50%;
}

/* GAME STATUS */
.status-strip {
    display: grid;
    grid-template-columns: minmax(280px, 2fr) 1fr 1fr;
    gap: 10px;
    margin: 0 0 14px;
}

.status-card {
    background: white;
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 12px 15px;
}

.status-card.primary {
    background: var(--vyoma-dark);
    border-color: var(--vyoma-dark);
}

.status-kicker {
    color: var(--muted);
    font-size: .7rem;
    font-weight: 800;
    letter-spacing: .7px;
    text-transform: uppercase;
}

.status-main {
    color: var(--vyoma-dark);
    font-size: 1.45rem;
    font-weight: 850;
    margin-top: 3px;
    line-height: 1.2;
}

.status-card.primary .status-kicker,
.status-card.primary .status-sub {
    color: #C9DDEF;
}

.status-card.primary .status-main {
    color: white;
    font-size: 1.62rem;
}

.status-sub {
    color: var(--muted);
    font-size: .76rem;
    margin-top: 3px;
}

/* PLAY SURFACE */
.section-heading {
    color: var(--ink);
    font-size: 1.28rem;
    font-weight: 850;
    margin-bottom: 2px;
}

.section-help {
    color: var(--muted);
    font-size: .84rem;
    line-height: 1.45;
    margin-bottom: 12px;
}

.input-divider {
    display: flex;
    align-items: center;
    gap: 10px;
    color: #8796A5;
    font-size: .72rem;
    font-weight: 800;
    letter-spacing: .5px;
    text-transform: uppercase;
    margin: 10px 0 4px;
}

.input-divider::before,
.input-divider::after {
    content: "";
    height: 1px;
    background: var(--line);
    flex: 1;
}

.review-ready {
    background: #EAF8F0;
    border: 1px solid #BFE3CD;
    border-left: 5px solid #2D8A55;
    border-radius: 11px;
    padding: 10px 12px;
    margin: 9px 0 12px;
    color: #215F3D;
    font-size: .83rem;
    font-weight: 700;
}

/* PREVIOUS VERSES */
.previous-card {
    background: #FFF9ED;
    border: 1px solid #F1DCAD;
    border-radius: 13px;
    padding: 11px 13px;
    margin: 10px 0 16px;
}

.previous-label {
    color: #6B7C93;
    font-size: .68rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .55px;
}

.previous-text {
    color: #243B53;
    font-size: .93rem;
    line-height: 1.45;
    margin-top: 4px;
}

/* HISTORY */
.timeline-heading {
    color: var(--ink);
    font-size: 1.35rem;
    font-weight: 850;
    margin: 1px 0 3px;
}

.move-card {
    background: white;
    border: 1px solid #E7EDF4;
    border-radius: 13px;
    padding: 12px 13px;
    margin-bottom: 10px;
}

.move-player {
    border-left: 5px solid var(--vyoma);
}

.move-computer {
    border-left: 5px solid #E48A2A;
}

.move-system {
    border-left: 5px solid #73889B;
    background: #F9FBFD;
}

.move-speaker {
    color: var(--ink);
    font-weight: 850;
    margin-bottom: 4px;
    font-size: .82rem;
}

.move-text {
    color: #243B53;
    line-height: 1.5;
    font-size: .98rem;
}

.move-meta {
    margin-top: 6px;
    color: #718096;
    font-size: .7rem;
}

/* TTS */
.tts-note {
    background: #EEF6FF;
    border: 1px solid #CFE3F6;
    border-radius: 10px;
    padding: 9px 10px;
    color: #315A7D;
    font-size: .76rem;
    line-height: 1.4;
}

/* FOOTER */
.footer-credit {
    margin-top: 28px;
    border-top: 1px solid #D9E3EC;
    padding-top: 14px;
    text-align: center;
    color: #6B7C93;
    font-size: .75rem;
}

.footer-credit img {
    width: 19px;
    height: 19px;
    border-radius: 50%;
    vertical-align: middle;
    margin-right: 5px;
}

/* STREAMLIT */
.stButton > button,
[data-testid="stFormSubmitButton"] > button {
    border-radius: 11px !important;
    font-weight: 800 !important;
    min-height: 2.65rem;
}

.stButton > button[kind="primary"] {
    background: var(--vyoma) !important;
    border-color: var(--vyoma) !important;
    color: white !important;
}

.stButton > button[kind="primary"]:hover {
    background: var(--vyoma-dark) !important;
    border-color: var(--vyoma-dark) !important;
}

.stTextArea textarea {
    border-radius: 12px !important;
    font-size: 1rem !important;
    line-height: 1.6 !important;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    background: white;
    border-color: var(--line) !important;
    border-radius: 16px !important;
}

div[data-testid="stMetric"] {
    background: rgba(255,255,255,.08);
    border-radius: 11px;
    padding: 8px 9px;
}

@media (max-width: 800px) {
    .status-strip {
        grid-template-columns: 1fr;
    }

    .app-header {
        align-items: flex-start;
        flex-direction: column;
        gap: 8px;
    }

    .brand-mark {
        display: none;
    }
}
</style>
"""
)

# ============================================================
# STATE
# ============================================================

def init_state() -> None:
    defaults = {
        "history": [],
        "used_ids": set(),
        "used_custom_texts": set(),
        "expected_letter": None,
        "free_start_allowed": True,
        "player_score": 0,
        "computer_score": 0,
        "chances_lost": 0,
        "game_over": False,
        "last_audio_digest": "",
        "verse_input": "",
        "pending_clear_input": False,
        "audio_nonce": 0,
        "last_tts_path": "",
        "last_tts_error": "",
        "last_error": "",
        "turn_feedback": "",
        "active_corpus": "",
        "session_token": uuid.uuid4().hex[:12],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def cleanup_last_tts() -> None:
    path = st.session_state.get("last_tts_path", "")

    if (
        path
        and path.startswith(tempfile.gettempdir())
        and os.path.exists(path)
    ):
        try:
            os.remove(path)
        except OSError:
            pass


def reset_game() -> None:
    cleanup_last_tts()

    st.session_state.history = []
    st.session_state.used_ids = set()
    st.session_state.used_custom_texts = set()
    st.session_state.expected_letter = None
    st.session_state.free_start_allowed = True
    st.session_state.player_score = 0
    st.session_state.computer_score = 0
    st.session_state.chances_lost = 0
    st.session_state.game_over = False
    st.session_state.last_audio_digest = ""
    st.session_state.verse_input = ""
    st.session_state.pending_clear_input = False
    st.session_state.audio_nonce += 1
    st.session_state.last_tts_path = ""
    st.session_state.last_tts_error = ""
    st.session_state.last_error = ""
    st.session_state.turn_feedback = ""


def clear_input() -> None:
    st.session_state.verse_input = ""
    st.session_state.last_audio_digest = ""
    st.session_state.last_error = ""
    st.session_state.audio_nonce += 1


init_state()

# ============================================================
# ENGINE
# ============================================================

@st.cache_resource(show_spinner=False)
def load_engine(csv_path: str) -> AntyakshariEngine:
    return AntyakshariEngine(csv_path)


def verse_reference(entry) -> str:
    chapter = str(entry.chapter or "").strip()
    number = str(entry.verse_number or "").strip()

    if chapter and number:
        return f"{chapter}.{number}"

    return number or str(entry.verse_id)


# ============================================================
# HISTORY
# ============================================================

def log_move(
    speaker: str,
    text: str,
    reference: str = "",
    note: str = "",
    required_letter: str = "",
) -> None:
    st.session_state.history.append(
        {
            "speaker": speaker,
            "text": text,
            "reference": reference,
            "note": note,
            "required_letter": required_letter,
        }
    )


def last_move(speaker: str):
    for move in reversed(st.session_state.history):
        if move["speaker"] == speaker:
            return move

    return None


def render_history() -> None:
    if not st.session_state.history:
        st.caption("Your accepted verses and computer replies will appear here.")
        return

    visible_turn = 0
    labelled_moves = []
    for move in st.session_state.history:
        speaker = move["speaker"]

        if speaker == "Player":
            visible_turn += 1
            css_class = "move-player"
            label = f"Round {visible_turn} · 👤 You"

        elif speaker == "Computer":
            css_class = "move-computer"
            label = f"Round {visible_turn} · 🤖 Computer"

        else:
            css_class = "move-system"
            label = "ℹ️ Game"

        labelled_moves.append((move, css_class, label))

    for move, css_class, label in reversed(labelled_moves):

        meta = []

        if move.get("reference"):
            meta.append("Ref: " + move["reference"])

        if move.get("required_letter"):
            meta.append("Required: " + move["required_letter"])

        if move.get("note"):
            meta.append(move["note"])

        safe_label = html.escape(label)
        safe_text = html.escape(str(move["text"]))
        safe_meta = html.escape(" · ".join(meta))

        st.html(
            f'<div class="move-card {css_class}">'
            f'<div class="move-speaker">{safe_label}</div>'
            f'<div class="move-text">{safe_text}</div>'
            f'<div class="move-meta">{safe_meta}</div>'
            f"</div>"
        )


# ============================================================
# GAME HELPERS
# ============================================================

def penalize(message: str) -> None:
    st.session_state.chances_lost += 1
    st.session_state.last_error = message
    st.session_state.turn_feedback = ""

    log_move(
        "System",
        message,
        note="Invalid move — one chance used",
    )

    if st.session_state.chances_lost >= MAX_CHANCES:
        st.session_state.game_over = True


def update_requirement(
    engine,
    bot_entry,
    rule_set: str,
) -> None:
    result = engine.next_required_start_for_entry(
        bot_entry,
        st.session_state.used_ids,
        rule_set=rule_set,
    )

    st.session_state.expected_letter = result["required_letter"]
    st.session_state.free_start_allowed = bool(
        result["free_start_allowed"]
    )

    if st.session_state.free_start_allowed:
        log_move(
            "System",
            (
                "No continuation remains in the "
                "selected corpus. "
                "Your next turn is a free start."
            ),
            note=str(result["rule_applied"]),
        )


def tts_output_path() -> str:
    return os.path.join(
        tempfile.gettempdir(),
        f"vagdhenu_{st.session_state.session_token}.wav",
    )


# ============================================================
# APP HEADER
# ============================================================

st.html(
    f'<div class="app-header">'
    f'<div><div class="app-title">🕉️ संस्कृत-अन्त्याक्षरी</div>'
    f'<div class="app-subtitle">Listen, continue, and keep the verse chain alive.</div></div>'
    f'<div class="brand-mark"><img src="{VYOMA_LOGO_URL}" alt="Vyoma">'
    f"<span>Vyoma Linguistic Labs</span></div>"
    f"</div>"
)

# ============================================================
# CORPUS
# ============================================================

available_corpora = available_corpus_files(".")

if not available_corpora:
    st.error("No supported corpus CSV files were found.")
    st.stop()

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.title("Game options")
    st.caption("Changes to the corpus start a new game.")

    corpus_label = st.selectbox(
        "Corpus",
        list(available_corpora.keys()),
    )

    corpus_path = available_corpora[corpus_label]

    verse_mode = st.radio(
        "Your verses",
        [
            VERSE_MODE_DATASET,
            VERSE_MODE_OPEN,
        ],
        help=(
            "Allow Other Verses preserves "
            "Vyoma's open mode: "
            "an outside Sanskrit verse can "
            "be accepted if it obeys the "
            "required starting अक्षर."
        ),
    )

    tts_ready = tts_available()

    tts_enabled = st.checkbox(
        "Play the computer’s chant",
        value=False,
        disabled=not tts_ready,
    )

    if tts_ready:
        st.caption(f"Voice: {tts_backend_name()}. Local generation can take a minute.")
    else:
        st.caption("Computer voice is unavailable.")

    with st.expander("Advanced rules"):
        rule_label = st.selectbox(
            "Continuation rule",
            list(RULE_LABELS.keys()),
            help=(
                "Strict uses the final playable अक्षर. Swara Fallback tries "
                "the recorded vowel only if no strict continuation remains."
            ),
        )

        difficulty = st.selectbox(
            "Computer strategy",
            DIFFICULTIES,
        )

        min_similarity = st.slider(
            "Corpus match tolerance",
            0.45,
            0.90,
            0.60,
            0.05,
        )

    rule_set = RULE_LABELS[rule_label]

    st.divider()

    if st.button(
        "Start a new game",
        type="primary",
        use_container_width=True,
    ):
        reset_game()
        st.rerun()

# ============================================================
# CORPUS CHANGE
# ============================================================

if (
    st.session_state.active_corpus
    and st.session_state.active_corpus != corpus_path
):
    reset_game()

st.session_state.active_corpus = corpus_path

engine = load_engine(corpus_path)

# ============================================================
# GAME STATUS
# ============================================================

chances_left = max(
    0,
    MAX_CHANCES - st.session_state.chances_lost,
)

hearts = (
    "❤️" * chances_left
    + "🖤" * st.session_state.chances_lost
)

chain_length = (
    st.session_state.player_score
    + st.session_state.computer_score
)

if (
    st.session_state.free_start_allowed
    or not st.session_state.expected_letter
):
    required_display = "Any अक्षर"
    required_sub = "Free start — choose any unused verse."
else:
    required_display = st.session_state.expected_letter
    required_sub = (
        "Your verse must begin with "
        f"{st.session_state.expected_letter}."
    )

st.html(
    '<div class="status-strip">'
    '<div class="status-card primary">'
    '<div class="status-kicker">Your next move</div>'
    f'<div class="status-main">{html.escape(required_display)}</div>'
    f'<div class="status-sub">{html.escape(required_sub)}</div>'
    "</div>"
    '<div class="status-card">'
    '<div class="status-kicker">Chances remaining</div>'
    f'<div class="status-main">{hearts}</div>'
    f'<div class="status-sub">{chances_left} '
    f"of {MAX_CHANCES} remaining</div>"
    "</div>"
    '<div class="status-card">'
    '<div class="status-kicker">Current chain</div>'
    f'<div class="status-main">{chain_length} verses</div>'
    '<div class="status-sub">'
    f"You {st.session_state.player_score}"
    " · "
    f"Computer {st.session_state.computer_score}"
    "</div>"
    "</div>"
    "</div>"
)

if st.session_state.turn_feedback:
    st.success(st.session_state.turn_feedback)

# ============================================================
# GAME OVER
# ============================================================

if st.session_state.game_over:
    st.error("Game Over — all 3 chances have been used.")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Your Valid Verses",
        st.session_state.player_score,
    )

    c2.metric(
        "Computer Verses",
        st.session_state.computer_score,
    )

    c3.metric(
        "Final Chain Length",
        chain_length,
    )

    st.info(
        "Open Game options and choose Start a new game to play again."
    )

# ============================================================
# MAIN LAYOUT
# ============================================================

left_col, right_col = st.columns(
    [1.08, 0.92],
    gap="large",
)

# ============================================================
# LEFT — PLAY
# ============================================================

with left_col:
    previous_computer = last_move("Computer")

    st.html(
        '<div class="section-heading">Your turn</div>'
        '<div class="section-help">Recite a verse or type it below. '
        'Review the text, then submit your move.</div>'
    )

    if previous_computer:
        st.html(
            '<div class="previous-card">'
            '<div class="previous-label">'
            "Computer just played"
            "</div>"
            '<div class="previous-text">'
            f'{html.escape(str(previous_computer["text"]))}'
            "</div>"
            "</div>"
        )

    if st.session_state.pending_clear_input:
        st.session_state.verse_input = ""
        st.session_state.pending_clear_input = False

    # ========================================================
    # AUDIO RECORDER
    # This is the recorder fix that worked locally.
    # ========================================================

    if st.session_state.game_over:
        audio_val = None
    else:
        audio_val = audiorecorder(
            "🎙️ Recite a verse",
            "⏹️ Finish recording",
            custom_style={
                "backgroundColor": "#FFFFFF",
                "border": "1px solid #DCE7F1",
                "borderRadius": "12px",
                "padding": "8px",
            },
            start_style={
                "backgroundColor": "#0B5FA5",
                "color": "#FFFFFF",
                "border": "0",
                "borderRadius": "9px",
                "fontWeight": "700",
            },
            stop_style={
                "backgroundColor": "#B42318",
                "color": "#FFFFFF",
                "border": "0",
                "borderRadius": "9px",
                "fontWeight": "700",
            },
            key=(
                "audio_input_"
                f"{st.session_state.audio_nonce}"
            ),
        )

    # ========================================================
    # SU-SROTA STT
    # ========================================================

    if (
        audio_val is not None
        and len(audio_val) > 0
        and not st.session_state.game_over
    ):
        audio_bytes = audio_val.export(
            format="wav"
        ).read()

        digest = hashlib.sha256(
            audio_bytes
        ).hexdigest()

        if digest != st.session_state.last_audio_digest:
            st.session_state.last_audio_digest = digest

            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
            ) as tmp:
                tmp.write(audio_bytes)
                temp_path = tmp.name

            try:
                with st.spinner(
                    "Su-śrotā is listening…"
                ):
                    recognized = transcribe_audio(
                        temp_path
                    )

                if recognized:
                    st.session_state.verse_input = (
                        recognized.strip()
                    )
                    st.session_state.last_error = ""
                else:
                    st.session_state.last_error = (
                        "Su-śrotā could not "
                        "transcribe this recording."
                    )

            finally:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    st.html('<div class="input-divider">or type your verse</div>')

    st.text_area(
        "Your verse",
        key="verse_input",
        height=135,
        placeholder=(
            "Your transcription appears here. You can also type or paste a verse."
        ),
        disabled=st.session_state.game_over,
    )

    if st.session_state.last_error:
        st.warning(
            st.session_state.last_error
        )

    submit_col, clear_col = st.columns(
        [2.2, 1]
    )

    submit_turn = submit_col.button(
        "Submit verse",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.game_over,
    )

    clear_col.button(
        "Clear",
        use_container_width=True,
        disabled=st.session_state.game_over,
        on_click=clear_input,
    )

    # ========================================================
    # SUBMIT TURN
    # ========================================================

    if (
        submit_turn
        and not st.session_state.game_over
    ):
        raw_user_text = (
            st.session_state
            .verse_input
            .strip()
        )

        if not raw_user_text:
            st.session_state.last_error = (
                "Record, type, or paste "
                "a verse before submitting."
            )

            st.rerun()

        (
            matched_entry,
            match_score,
        ) = engine.match_verse(
            raw_user_text,
            min_similarity=float(
                min_similarity
            ),
        )

        matched_in_dataset = (
            matched_entry is not None
        )

        # ----------------------------------------------------
        # DATASET MODE
        # ----------------------------------------------------

        if (
            verse_mode == VERSE_MODE_DATASET
            and not matched_in_dataset
        ):
            penalize(
                "That recitation did not "
                "match a verse in the "
                "selected corpus closely enough."
            )

            st.rerun()

        # ----------------------------------------------------
        # DATASET VERSE
        # ----------------------------------------------------

        if matched_in_dataset:
            player_text = (
                matched_entry.verse
            )

            player_first = (
                matched_entry.first_letter
            )

            player_last = (
                matched_entry.last_letter
            )

            player_swara = (
                matched_entry.swara_after_last
            )

            player_reference = (
                verse_reference(
                    matched_entry
                )
            )

            if (
                matched_entry.verse_id
                in st.session_state.used_ids
            ):
                penalize(
                    "That verse has "
                    "already been used."
                )

                st.rerun()

        # ----------------------------------------------------
        # OPEN VERSE
        # ----------------------------------------------------

        else:
            player_text = raw_user_text

            normalized_custom = (
                normalize_devanagari_text(
                    player_text
                )
            )

            if not normalized_custom:
                penalize(
                    "Could not detect usable "
                    "Devanagari text in that verse."
                )

                st.rerun()

            if (
                normalized_custom
                in st.session_state.used_custom_texts
            ):
                penalize(
                    "That outside-dataset "
                    "verse has already been used."
                )

                st.rerun()

            player_first = (
                infer_first_letter(
                    player_text
                )
            )

            (
                player_last,
                player_swara,
            ) = infer_last_letter_and_swara(
                player_text
            )

            player_reference = (
                "Outside selected corpus"
            )

            if (
                not player_first
                or not player_last
            ):
                penalize(
                    "Could not determine "
                    "the starting or ending अक्षर."
                )

                st.rerun()

        # ----------------------------------------------------
        # CHECK REQUIRED LETTER
        # ----------------------------------------------------

        if (
            not st.session_state.free_start_allowed
            and st.session_state.expected_letter
            and player_first
            != st.session_state.expected_letter
        ):
            penalize(
                "Wrong starting अक्षर. "
                f"This turn required "
                f"{st.session_state.expected_letter}, "
                f"but the submitted verse "
                f"begins with {player_first}."
            )

            st.rerun()

        # ----------------------------------------------------
        # MARK PLAYER VERSE USED
        # ----------------------------------------------------

        if matched_in_dataset:
            st.session_state.used_ids.add(
                matched_entry.verse_id
            )

            correction_note = ""

            if (
                normalize_devanagari_text(
                    raw_user_text
                )
                !=
                normalize_devanagari_text(
                    player_text
                )
            ):
                correction_note = (
                    "Matched corpus verse "
                    f"({match_score:.0%})."
                )

        else:
            st.session_state.used_custom_texts.add(
                normalize_devanagari_text(
                    player_text
                )
            )

            correction_note = (
                "Accepted through "
                "Allow Other Verses."
            )

        old_required = (
            st.session_state.expected_letter
            or ""
        )

        st.session_state.player_score += 1
        st.session_state.last_error = ""

        log_move(
            "Player",
            player_text,
            reference=player_reference,
            note=correction_note,
            required_letter=old_required,
        )

        # ----------------------------------------------------
        # COMPUTER RESPONSE
        # ----------------------------------------------------

        response = (
            engine
            .choose_response_for_end(
                player_last,
                player_swara,
                st.session_state.used_ids,
                rule_set=rule_set,
                difficulty=difficulty,
            )
        )

        bot_entry = (
            response["bot_entry"]
        )

        # ----------------------------------------------------
        # COMPUTER HAS NO VERSE
        # ----------------------------------------------------

        if bot_entry is None:

            st.session_state.expected_letter = (
                None
            )

            st.session_state.free_start_allowed = (
                True
            )

            cleanup_last_tts()

            st.session_state.last_tts_path = ""
            st.session_state.last_tts_error = ""

            st.session_state.turn_feedback = (
                "✓ Your verse was accepted. "
                "The computer has no continuation, "
                "so your next turn is a free start."
            )

            log_move(
                "System",
                (
                    "The computer has no unused "
                    "continuation in this corpus. "
                    "Free start is enabled."
                ),
                note=str(
                    response["rule_applied"]
                ),
            )

        # ----------------------------------------------------
        # COMPUTER PLAYS
        # ----------------------------------------------------

        else:
            st.session_state.used_ids.add(
                bot_entry.verse_id
            )

            st.session_state.computer_score += 1

            log_move(
                "Computer",
                bot_entry.verse,
                reference=verse_reference(
                    bot_entry
                ),
                note=str(
                    response["rule_applied"]
                ),
                required_letter=str(
                    response["required_letter"]
                    or ""
                ),
            )

            update_requirement(
                engine,
                bot_entry,
                rule_set,
            )

            if (
                st.session_state.free_start_allowed
                or not st.session_state.expected_letter
            ):
                next_text = "free start"

            else:
                next_text = (
                    st.session_state
                    .expected_letter
                )

            st.session_state.turn_feedback = (
                "✓ Verse accepted. "
                "The computer replied. "
                "Your next required अक्षर is "
                f"{next_text}."
            )

            # ------------------------------------------------
            # VAGDHENU
            # ------------------------------------------------

            cleanup_last_tts()

            st.session_state.last_tts_path = ""
            st.session_state.last_tts_error = ""

            if tts_enabled:

                with st.spinner(
                    "Vāgdhenu is generating "
                    "the computer's chant…"
                ):

                    audio_path = (
                        generate_speech(
                            bot_entry.verse,
                            tts_output_path(),
                        )
                    )

                st.session_state.last_tts_path = (
                    audio_path
                    or ""
                )

                st.session_state.last_tts_error = (
                    get_last_tts_error()
                )

        # ----------------------------------------------------
        # PREPARE NEXT TURN
        # ----------------------------------------------------

        st.session_state.pending_clear_input = (
            True
        )

        st.session_state.last_audio_digest = ""

        st.session_state.audio_nonce += 1

        st.rerun()

    # ========================================================
    # COMPUTER AUDIO
    # ========================================================

    if (
        st.session_state.last_tts_path
        and os.path.exists(
            st.session_state.last_tts_path
        )
    ):

        with st.container(
            border=True
        ):

            st.subheader(
                "🔊 Computer Chant"
            )

            st.audio(
                st.session_state.last_tts_path,
                format="audio/wav",
            )

            st.caption(
                "Generated through "
                f"{tts_backend_name()}."
            )

    elif st.session_state.last_tts_error:

        st.warning(
            "The computer move was valid, "
            "but Vāgdhenu audio failed: "
            +
            st.session_state.last_tts_error
        )

# ============================================================
# RIGHT — HISTORY
# ============================================================

with right_col:

    with st.container(
        border=True
    ):

        st.html(
            '<div class="timeline-heading">'
            "📜 Verse Chain"
            "</div>"
        )

        st.caption(
            "Latest move first"
        )

        render_history()

    # --------------------------------------------------------
    # RULE HELP
    # --------------------------------------------------------

    with st.expander(
        "Rules & modes"
    ):

        st.markdown(
            f"""
**Strict — last अक्षर only**  
The next verse must begin with the previous verse's last playable अक्षर.

**Swara Fallback**  
The game uses the same strict rule first. Only when no strict continuation exists does it try the recorded **Swara After Last**.

**{VERSE_MODE_DATASET}**  
Your verse must match the selected corpus.

**{VERSE_MODE_OPEN}**  
Preserves the original Vyoma open setting. A Sanskrit verse outside the selected corpus may be accepted if it follows the required starting अक्षर.

**Chances**  
You have **{MAX_CHANCES} chances**. A wrong starting अक्षर, repeated verse, or invalid submission uses one chance.
"""
        )

# ============================================================
# FOOTER
# ============================================================

st.html(
    f'<div class="footer-credit">'
    f'<img '
    f'src="{VYOMA_LOGO_URL}" '
    f'alt="Vyoma">'
    f"Based on the original "
    f'<a '
    f'href="{VYOMA_REPO_URL}" '
    f'target="_blank">'
    f"Vyoma Linguistic Labs "
    f"Antyakshari-Krida"
    f"</a> project · "
    f"Su-śrotā ASR · "
    f"Vāgdhenu Sanskrit chant."
    f"</div>"
)

"""Fixed engineering constants: values not env-tunable (config.py holds the tunable ones)."""

BYTES_PER_MB: int = 1024 * 1024

# ---- Arabic character data for normalization and direction detection ----
# Data (character sets and mappings), not prose, so chartered here. See DECISIONS.md.
ARABIC_DIACRITICS_AND_PUNCT_PATTERN: str = r"[ً-ْٰۖ-ۭـ]|[^\w\s]"
ARABIC_ALEF_FORMS: str = "أإآٱ"
ARABIC_ALEF_CANONICAL: str = "ا"
ARABIC_HAMZA_FORMS: str = "ؤئ"
ARABIC_HAMZA_CANONICAL: str = "ء"
ARABIC_TA_MARBUTA: str = "ة"
ARABIC_TA_CANONICAL: str = "ه"
# The Arabic comma used to join attendee names in a reduce summary line (data,
# not prose), chartered beside the other Arabic literals.
ARABIC_COMMA: str = "،"
# Arabic and friends including presentation forms; everything else is LTR.
ARABIC_RTL_RANGES: str = r"؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿"

# ---- HTTP / Groq provider ----
GROQ_API_BASE: str = "https://api.groq.com/openai/v1"
STT_API_PATH: str = "/audio/transcriptions"
LLM_API_PATH: str = "/chat/completions"
MODELS_API_PATH: str = "/models"
HTTP_RETRIES: int = 2  # retries after the first attempt
RETRY_BACKOFF_BASE_S: float = 2.0
RETRY_AFTER_HEADER: str = "retry-after"
RETRY_AFTER_MAX_S: float = 70.0  # one tokens-per-minute window, then fall back
# A uniform jitter up to this value is added to every retry sleep so parallel
# provider calls that rate-limit together do not retry in lockstep.
HTTP_JITTER_S: float = 0.5
STT_TIMEOUT_S: float = 120.0
LLM_TIMEOUT_S: float = 180.0
MODELS_TIMEOUT_S: float = 15.0
ERROR_SNIPPET_CHARS: int = 200
LLM_TEMPERATURE: float = 0.2
MAX_COMPLETION_TOKENS: int = 4000

# ---- Uploads ----
UPLOAD_CHUNK_BYTES: int = BYTES_PER_MB
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({"webm", "ogg", "wav", "mp3", "m4a", "mp4"})
PREVIEW_BYTES_PER_SECOND: int = 8000  # mp3 at 64kbit mono

# ---- Job identity and labels ----
JOB_ID_LENGTH: int = 12
MAX_LABEL_LENGTH: int = 40

# ---- STT long-file splitting ----
MAX_SINGLE_UPLOAD_BYTES: int = 24 * BYTES_PER_MB  # Groq per-file cap is 25 MB
SPLIT_PART_LENGTH_S: int = 600
SILENCE_NOISE_DB: str = "-35dB"
SILENCE_MIN_DURATION_S: float = 0.6
SPLIT_SEARCH_BACK_S: int = 90
SPLIT_SEARCH_FORWARD_S: int = 30
SPLIT_EDGE_MARGIN_S: int = 5
SPLIT_MIN_PART_S: float = 1.0
PART_WORD_OVERLAP_S: float = 0.5  # tolerate words a hair past a part boundary

# ---- Sentence segmentation (see tests/test_sentences.py) ----
SENTENCE_PAUSE_GAP_S: float = 0.75
SENTENCE_MAX_WORDS: int = 30
SENTENCE_MAX_DURATION_S: float = 18.0
SENTENCE_TERMINATORS: frozenset[str] = frozenset({".", "؟", "!", "؛"})
ARABIC_HONORIFICS: frozenset[str] = frozenset({"د.", "أ.", "م.", "أ.د.", "ب.", "ج."})

# ---- Whisper silence hallucination cleanup (processing/cleanup.py) ----
# At this threshold whisper's no_speech_prob segment mark is trusted as silence:
NO_SPEECH_PROB_MAX: float = 0.6

# ---- LLM prompt budget (Groq free tier is ~8K real tokens/min for gpt-oss-120b) ----
# Token estimate = chars / CHARS_PER_TOKEN, deliberately conservative. See DECISIONS.md.
MAX_PROMPT_TOKENS: int = 8550
CHARS_PER_TOKEN: float = 1.25  # conservative Arabic chars-per-token estimate
CORRECTION_ERRORS_TAIL_CHARS: int = 800
CITATION_MIN_TOKEN_CHARS: int = 3  # shorter tokens never count as overlap evidence

# ---- Map-reduce analysis for over-budget transcripts ----
# Over-budget transcripts split into windows; per-window overhead measured. See DECISIONS.md.
PROMPT_OVERHEAD_EST_TOKENS: int = 3180  # system prompt + header + window scope
# Worst-case allowance on top of a full window (completion tokens and one
# corrective retry share the same TPM window as the prompt).
SAFETY_MARGIN_TOKENS: int = 370
# One window's transcript budget, derived so window + overhead + margin can
# never exceed MAX_PROMPT_TOKENS. Never edit the three inputs independently.
WINDOW_TOKEN_BUDGET: int = (
    MAX_PROMPT_TOKENS - PROMPT_OVERHEAD_EST_TOKENS - SAFETY_MARGIN_TOKENS
)  # = 5000: one map window: transcript + shared prompt stay under MAX
# The reduce call's own system prompt, including the shared schema example.
REDUCE_PROMPT_OVERHEAD_EST_TOKENS: int = 1740  # >= estimate_tokens(REDUCE_SYSTEM_PROMPT)
REDUCE_TOKEN_BUDGET: int = (
    MAX_PROMPT_TOKENS - REDUCE_PROMPT_OVERHEAD_EST_TOKENS - SAFETY_MARGIN_TOKENS
)  # = 6440: budget for the reduce user message alone (window summaries only,
# never the transcript). The system prompt is paid for by the overhead term
# above, so the budget checks compare only the joined summaries against this.
MAP_OVERLAP_MIN_TOKENS: int = 3  # minimum shared content tokens to fuse two mapped items
MAP_TITLE_OVERLAP_MAX_TOKENS: int = (
    2  # a heading-length summary (<= this) fuses on full containment
)
REDUCE_ITEM_PREVIEW_CHARS: int = 80  # one-line preview logged when the reduce input overflows
REDUCE_SUMMARY_MAX_ITEMS: int = (
    60  # a reduce input past this many summaries is truncated, never silent
)

# ---- Default chat model and the retired-model preflight ----
# openai/gpt-oss-120b replaced the deprecated models on 2026-08-18. See docs/DECISIONS.md.
DEFAULT_LLM_MODEL: str = "openai/gpt-oss-120b"

# Chat models named to the user when the configured one is retired, verified
# against GET /openai/v1/models on 2026-08-18. See docs/DECISIONS.md.
FALLBACK_CHAT_MODELS: tuple[str, ...] = (
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
    "allam-2-7b",
)
CHAT_MODEL_SUGGESTION_COUNT: int = 3

# ---- Offline/local providers (STT_PROVIDER=local, LLM_PROVIDER=local) ----
# Cloud default path untouched; these apply only on the local fallback. See DECISIONS.md.
DEFAULT_LOCAL_STT_MODEL: str = "large-v3-turbo"  # faster-whisper Arabic model
DEFAULT_LOCAL_LLM_MODEL: str = "qwen3:8b"  # pulled by the compose ollama service
DEFAULT_OLLAMA_URL: str = "http://ollama:11434/v1"  # OpenAI-compatible, no auth

# ---- ffmpeg subprocess ----
FFMPEG_TIMEOUT_S: int = 660  # covers the longest expected single conversion

# ---- Export ----
INCLUDE_TRANSCRIPT_IN_DOCX: bool = True  # appendix of stamped transcript lines
DOCX_FILENAME_TEMPLATE: str = "mahdar-{job_id}.docx"
JSON_FILENAME_TEMPLATE: str = "mahdar-{job_id}.json"
DOCX_MEDIA_TYPE: str = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# ---- Diarization RAM: the one intentional whole-file-in-memory case ----
# pyannote decodes the full waveform to RAM by design; documented in README "Audio handling".
DIARIZATION_RAM_BYTES_PER_SECOND: int = 16000 * 4

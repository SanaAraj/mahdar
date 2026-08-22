BYTES_PER_MB: int = 1024 * 1024


ARABIC_DIACRITICS_AND_PUNCT_PATTERN: str = r"[ً-ْٰۖ-ۭـ]|[^\w\s]"
ARABIC_ALEF_FORMS: str = "أإآٱ"
ARABIC_ALEF_CANONICAL: str = "ا"
ARABIC_HAMZA_FORMS: str = "ؤئ"
ARABIC_HAMZA_CANONICAL: str = "ء"
ARABIC_TA_MARBUTA: str = "ة"
ARABIC_TA_CANONICAL: str = "ه"


ARABIC_COMMA: str = "،"

ARABIC_RTL_RANGES: str = r"؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿"


GROQ_API_BASE: str = "https://api.groq.com/openai/v1"
COHERE_API_BASE: str = "https://api.cohere.com/v2"
STT_API_PATH: str = "/audio/transcriptions"
LLM_API_PATH: str = "/chat/completions"
MODELS_API_PATH: str = "/models"
HTTP_RETRIES: int = 2
RETRY_BACKOFF_BASE_S: float = 2.0
RETRY_AFTER_HEADER: str = "retry-after"
RETRY_AFTER_MAX_S: float = 70.0


HTTP_JITTER_S: float = 0.5
STT_TIMEOUT_S: float = 120.0
LLM_TIMEOUT_S: float = 180.0
MODELS_TIMEOUT_S: float = 15.0
ERROR_SNIPPET_CHARS: int = 200
LLM_TEMPERATURE: float = 0.2
MAX_COMPLETION_TOKENS: int = 4000


UPLOAD_CHUNK_BYTES: int = BYTES_PER_MB
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({"webm", "ogg", "wav", "mp3", "m4a", "mp4"})
AUDIO_HEADER_BYTES: int = 64


JOB_ID_LENGTH: int = 12
MAX_LABEL_LENGTH: int = 40


MAX_SINGLE_UPLOAD_BYTES: int = 24 * BYTES_PER_MB
SPLIT_PART_LENGTH_S: int = 600
SILENCE_NOISE_DB: str = "-35dB"
SILENCE_MIN_DURATION_S: float = 0.6
SPLIT_SEARCH_BACK_S: int = 90
SPLIT_SEARCH_FORWARD_S: int = 30
SPLIT_EDGE_MARGIN_S: int = 5
SPLIT_MIN_PART_S: float = 1.0
PART_WORD_OVERLAP_S: float = 0.5


SENTENCE_PAUSE_GAP_S: float = 0.75
SENTENCE_MAX_WORDS: int = 30
SENTENCE_MAX_DURATION_S: float = 18.0
SENTENCE_TERMINATORS: frozenset[str] = frozenset({".", "؟", "!", "؛"})
ARABIC_HONORIFICS: frozenset[str] = frozenset({"د.", "أ.", "م.", "أ.د.", "ب.", "ج."})


NO_SPEECH_PROB_MAX: float = 0.6


MAX_PROMPT_TOKENS: int = 8550
CHARS_PER_TOKEN: float = 1.25
CORRECTION_ERRORS_TAIL_CHARS: int = 800
CITATION_MIN_TOKEN_CHARS: int = 3


PROMPT_OVERHEAD_EST_TOKENS: int = 3180


SAFETY_MARGIN_TOKENS: int = 370


WINDOW_TOKEN_BUDGET: int = MAX_PROMPT_TOKENS - PROMPT_OVERHEAD_EST_TOKENS - SAFETY_MARGIN_TOKENS

REDUCE_PROMPT_OVERHEAD_EST_TOKENS: int = 1740
REDUCE_TOKEN_BUDGET: int = (
    MAX_PROMPT_TOKENS - REDUCE_PROMPT_OVERHEAD_EST_TOKENS - SAFETY_MARGIN_TOKENS
)


MAP_OVERLAP_MIN_TOKENS: int = 3
MAP_TITLE_OVERLAP_MAX_TOKENS: int = 2
REDUCE_ITEM_PREVIEW_CHARS: int = 80
REDUCE_SUMMARY_MAX_ITEMS: int = 60


DEFAULT_LLM_MODEL: str = "openai/gpt-oss-120b"
DEFAULT_COHERE_STT_MODEL: str = "cohere-transcribe-arabic-07-2026"


FALLBACK_CHAT_MODELS: tuple[str, ...] = (
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
    "allam-2-7b",
)
CHAT_MODEL_SUGGESTION_COUNT: int = 3


DEFAULT_LOCAL_STT_MODEL: str = "large-v3-turbo"
DEFAULT_LOCAL_LLM_MODEL: str = "qwen3:8b"
DEFAULT_OLLAMA_URL: str = "http://ollama:11434/v1"


FFMPEG_TIMEOUT_S: int = 660


INCLUDE_TRANSCRIPT_IN_DOCX: bool = True
DOCX_FILENAME_TEMPLATE: str = "mahdar-{job_id}.docx"
JSON_FILENAME_TEMPLATE: str = "mahdar-{job_id}.json"
DOCX_MEDIA_TYPE: str = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.app import constants

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    stt_provider: str = "groq"
    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_stt_model: str = "whisper-large-v3"
    groq_llm_model: str = constants.DEFAULT_LLM_MODEL
    local_stt_model: str = constants.DEFAULT_LOCAL_STT_MODEL
    local_llm_model: str = constants.DEFAULT_LOCAL_LLM_MODEL
    ollama_url: str = constants.DEFAULT_OLLAMA_URL
    hf_token: str = ""
    max_upload_mb: int = 500
    data_dir: Path = Path("/data")

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * constants.BYTES_PER_MB


# For local runs outside Docker, look for the user's ffmpeg/ffprobe beside the
# project toolchain (see DECISIONS.md). Inside the container ffmpeg is already
# on PATH, so this only ever helps, never hides a system install.
_LOCAL_BIN = Path.home() / "ffmpeg" / "bin"
if _LOCAL_BIN.is_dir() and str(_LOCAL_BIN) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = str(_LOCAL_BIN) + os.pathsep + os.environ.get("PATH", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()

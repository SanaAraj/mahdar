import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app import constants

_APP_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_APP_DIR.parent.parent / ".env", _APP_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
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


# Local dev on a Mac without a system ffmpeg: a static ffmpeg/ffprobe build
# unpacked under ~/ffmpeg/bin goes on PATH so runs outside Docker find it.
# Inside the container the directory does not exist and this is a no-op.
_LOCAL_BIN = Path.home() / "ffmpeg" / "bin"
if _LOCAL_BIN.is_dir() and str(_LOCAL_BIN) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = str(_LOCAL_BIN) + os.pathsep + os.environ.get("PATH", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()

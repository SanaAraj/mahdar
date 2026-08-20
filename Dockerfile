FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# ffmpeg: audio conversion plus the libav shared libraries torchcodec needs to
# decode inside pyannote. curl: the healthcheck. libgomp1: torch's OpenMP runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

# The official CPU-only torch index avoids pulling the large Nvidia/CUDA wheels.
COPY requirements.txt ./
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend
COPY pyproject.toml ./

RUN useradd --create-home --uid 10001 mahdar \
    && mkdir -p /data/hf \
    && chown -R mahdar:mahdar /data /srv

USER mahdar

EXPOSE 8100

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8100/api/health || exit 1

# One worker by design: job state lives in an in-memory registry and the
# pipeline runs on background threads in this process, so a second worker
# would split state. See docs/DECISIONS.md.
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8100", "--workers", "1"]

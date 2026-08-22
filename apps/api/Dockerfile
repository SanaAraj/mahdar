FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /srv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev
COPY app ./app
RUN uv sync --frozen --no-dev

FROM python:3.12-slim

# ffmpeg: audio conversion plus the libav shared libraries torchcodec needs to
# decode inside pyannote. curl: the healthcheck. libgomp1: torch's OpenMP runtime.
# Torch wheels are glibc-only (no musl), so bookworm-slim rather than alpine.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY --from=builder /srv/.venv /srv/.venv
COPY --from=builder /srv/app /srv/app
COPY pyproject.toml ./

RUN useradd --create-home --uid 10001 mahdar \
    && mkdir -p /data/hf \
    && chown -R mahdar:mahdar /data /srv

USER mahdar

ENV PATH="/srv/.venv/bin:$PATH" PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

# One worker by design: job state lives in an in-memory registry and the
# pipeline runs on background threads in this process, so a second worker
# would split state. See docs/DECISIONS.md.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

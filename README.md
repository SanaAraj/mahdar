# محضر (Mahdar)

A small app that turns a recorded meeting into a usable Arabic minutes
document. Press record, speak, stop — محضر gives you back a timestamped
transcript, per-speaker labels you can edit, and a clean minutes page with
every topic, decision, directive, and task, each one linked to the exact
sentences it was taken from.

No dashboards. No accounts. One page, one job, your data on your own machine.

## What it does

- **Record in the browser or upload a file** (webm, ogg, wav, mp3, m4a, mp4)
- **Live capture** with a volume meter, pause / resume, and a timer, plus
  drag-and-drop and a progress bar
- **Sentence-level transcript** with timestamps; clicking a line seeks the
  audio to that exact moment
- **Speaker separation** with editable names; saving a name automatically
  refreshes the minutes before exports are available again
- **Minutes extraction** in Arabic: عنوان الاجتماع, المواضيع, القرارات,
  التوجيهات, and a tasks table with owner, Arabic priority, and the deadline
  normalized to Hijri *and* Gregorian dates
- **Export** as a well-formed DOCX (proper right-to-left) or JSON
- Designed for Arabic from the start: the whole interface is RTL, written in
  Arabic, and the processing pipeline treats Arabic as the source of truth

### If you prefer to stay offline

Set `STT_PROVIDER=local` and `LLM_PROVIDER=local` in `.env` and run
`docker compose --profile local up`. محضر then transcribes with
faster-whisper and extracts minutes with a local Ollama model, with no
outbound network calls at all. Cloud remains the default (Groq free tier) for
speed; switch per environment, not per project.

## Run

```bash
cp .env.example .env        # add GROQ_API_KEY and HF_TOKEN
docker compose up --build   # one command starts the complete app on port 8100
```

Open http://localhost:8100. Press record, upload, get your minutes.

## Why it's built this way

A few deliberate choices show up in the code as hard rules:

- **Verified by construction.** Every extracted item in the minutes has to
  cite the exact sentences it is based on; items without a clean citation
  are dropped so the document never invents details.
- **Provider-flexible, cost-transparent.** STT and the minutes LLM swap
  between Groq and local services through one interface. The prompt asks the
  model for Arabic fields inside an English contract, which survived a model
  swap in June 2026 without a single regression.
- **One workflow, three containers.** Caddy exposes one origin, React serves
  the page, and one FastAPI worker owns the job registry. State is one JSON
  file per meeting on a named Docker volume. No Redis, Celery, or SQL server.
- **Resilient at the seams.** Long recordings are split at silence points so
  a 25 MB provider cap never becomes your problem; LLM responses that omit
  the schema are re-asked; empty audio, full queues, and missing keys all
  surface as clear Arabic messages rather than stack traces.

## Stack

- **Web** — React 19 + TanStack Start on Bun, Tailwind CSS v4, shadcn over
  Radix primitives. Fully RTL, fully Arabic, light only.
- **API** — FastAPI + uv (Python 3.12), ffmpeg for audio work, pyannote for
  diarization, python-docx for the Word export, slowapi on the upload and
  analysis endpoints.
- **Infra** — Turborepo at the root, one compose file that brings up Caddy
  (single origin on :8100), the API, and the web app. An optional Ollama
  service handles fully-offline mode.

Layout is accidentally also the documentation:

```
apps/api   Python, feature-first packages (meetings / transcription /
           diarization / analysis / export)
apps/web   React, routes + per-feature components + hooks
docs/      Dated decision log — the why, not the what
samples/   Small real Arabic test clips
```

## Development

```bash
bun install --frozen-lockfile
bun run dev                 # api on :8100, web on :3000, hot reload both
bun run lint
bun run typecheck
bun run test
```

The web app at :3000 proxies `/api/*` to the api on :8100, mirroring
production.

## Configuration

`.env.example` lists every key. The two you'll usually care about:
`GROQ_API_KEY` for the cloud path, and `HF_TOKEN` (free, read access) to
enable speaker separation inside the local containers. The rest are sane
defaults; see each comment for what it does.

## For contributors

- All user-facing text is Arabic (the app is for Arabic speakers); all code
  identifiers, log lines, comments, READMEs, DECISIONS, and commit messages
  are English.
- The single source of truth for Arabic copy is `apps/api/app/strings.py`
  on the server and `apps/web/src/lib/strings.ts` on the web. No Arabic
  string lives anywhere else.
- Design choices are recorded one per day in `docs/DECISIONS.md`; the latest
  entry always describes the current layout, providers, and ports.
- Tests run the pipeline with provider calls mocked, so a network outage
  cannot fail the automated suite.

## What "good" looks like

1. Record → stop → the page switches to processing, stages tick by.
2. When done, the transcript appears; clicking a line seeks the audio.
3. Rename "المتحدث 1" to a real name — re-analysis starts automatically.
4. Export DOCX. Attach it to the meeting invite.

## Ready-made vs built here

| Ready-made component | Role |
| --- | --- |
| FastAPI, Starlette, uvicorn | HTTP API and runtime |
| React, TanStack Start, TanStack Query | Browser application and server state |
| Caddy | Single public origin and API routing |
| ffmpeg and ffprobe | Audio conversion, probing, and splitting |
| Whisper large-v3 through Groq | Default cloud transcription |
| pyannote community-1 | Local speaker diarization |
| faster-whisper and Ollama | Offline transcription and minutes fallback |
| python-docx and hijridate | RTL Word export and Hijri conversion |

Built in this repository: browser recording and upload, the processing-stage
workflow, sentence assembly, speaker attribution and renaming, source-linked
minutes and tasks, faithfulness guards, deterministic date normalization,
long-recording map-reduce, Arabic error handling, audio seeking, and RTL DOCX
generation.

## Known limits

- Groq is the default path and sends audio and transcript context to an
  external service. The local profile avoids outbound provider calls but is
  slower on CPU and downloads several gigabytes of model weights on first use.
- Speaker diarization needs a Hugging Face token with access to the gated
  pyannote model. Without it, transcription and minutes remain available.
- Diarization holds one decoded waveform in memory, approximately 230 MB per
  hour of mono 16 kHz audio.
- Arabic transcription can mishear names, dialect, or similar-sounding words.
  The generated minutes stay grounded in the transcript and do not silently
  correct uncertain speech.
- The Groq free tier can rate-limit bursts. The transcript is retained and
  analysis can be retried.
- The local LLM produces weaker Arabic minutes than the configured Groq model,
  especially for long or dialect-heavy meetings.
- No demonstration video is included; it is optional in the task brief.

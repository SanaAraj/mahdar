# Mahdar

A single-page Arabic meeting recorder. You record a meeting in the browser
(or upload a file), and the server returns an Arabic transcript with
sentence timestamps, speaker separation, and a minutes document with topics,
decisions, directives, and tasks. Every extracted item cites the transcript
sentences it rests on, so nothing in the minutes is a guess.

## Run it

```bash
cp .env.example .env
# set GROQ_API_KEY (free key from console.groq.com)
# set HF_TOKEN if you want speaker separation
docker compose up
```

Open http://localhost:8100. The Groq key is the only hard requirement.
Speaker separation needs a free Hugging Face read token that has accepted
the terms of pyannote/speaker-diarization-community-1; without it, meetings
still transcribe and analyze and the diarize stage shows as skipped.

Jobs and model caches live on the named volume `mahdar-data`. To wipe
everything: `docker compose down -v`.

Recording needs Chrome or Edge (MediaRecorder with webm). File upload works
in any modern browser.

### Settings (.env)

| Variable | Default | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | (empty) | Transcription and minutes extraction. Required. |
| `HF_TOKEN` | (empty) | Enables local pyannote diarization. |
| `GROQ_STT_MODEL` | `whisper-large-v3` | Speech-to-text model. |
| `GROQ_LLM_MODEL` | `openai/gpt-oss-120b` | Chat model for the minutes. |
| `STT_PROVIDER` / `LLM_PROVIDER` | `groq` | `groq` (cloud) or `local` (offline). |
| `LOCAL_STT_MODEL` | `large-v3-turbo` | faster-whisper model for local STT. |
| `LOCAL_LLM_MODEL` | `qwen3:8b` | Ollama model for local minutes. |
| `OLLAMA_URL` | `http://ollama:11434/v1` | Where the app reaches the local LLM. |
| `MAX_UPLOAD_MB` | `500` | Upload size cap. |
| `DATA_DIR` | `/data` | Job state and derived audio. |

## What you get

- Live recording with a level indicator, timer, pause and resume; upload as
  the backup path.
- A stage list while processing: convert, transcribe, diarize, assemble,
  analyze.
- Clicking any sentence, minutes item, or task jumps the player to where it
  was said. Items without a resolvable source stay plain.
- Speakers can be renamed from the page (with a short voice sample to tell
  them apart); renaming re-runs the minutes with the new names.
- Spoken dates like "tomorrow", "end of next month", or a Hijri date are
  resolved to Gregorian and Hijri by code anchored to the meeting date. The
  model never computes a date, and unparseable phrases stay null.
- Export as JSON or as an Arabic DOCX with real RTL: every paragraph is
  bidi, the tasks table is bidiVisual, and Latin terms and digits keep their
  direction inside Arabic text. Exports of an unfinished meeting answer 409.

## Architecture

One FastAPI service, one uvicorn worker, no database: each meeting is a JSON
file under `/data`. The pipeline runs on background threads.

```
browser (record/upload)
        |
        v
POST /api/meetings  --stream-to-disk-->  data/<id>/original.<ext>
        |                                       |
        v                                       v
   JobRegistry <--- state.json --- ffmpeg convert (disk to disk)
   (background threads)                     |        |
        |                          audio.wav 16k  audio.mp3 64k
        v                                       |
  +----------------+   parallel   +-------------+-----------+
  | transcribe     |              | diarize (pyannote, RAM) |
  | Groq or local  |              | words.json / turns.json |
  +----------------+              +-------------------------+
        |                                       |
        +----------------> assemble -----------+  sentences + speakers
                                |
                                v
                    analyze (chat LLM, prompt with [sN] ids)
                                |
                                v
            state.json (status, stages, sentences, speakers, analysis)
```

The parts that took real work:

- Sentences close on pauses, terminators, hard word and duration limits, and
  diarized speaker changes, so one sentence never carries two speakers.
- Whisper invents text on silence. Words in segments with high
  no_speech_prob are dropped and repeated-sentence loops collapse; a silent
  upload produces zero sentences, not a fake transcript.
- Every topic, decision, directive, and task must cite sentence ids that
  exist and share wording with what it claims; anything else is dropped.
- Uploads over Groq's 25 MB cap are split at silence with a running offset,
  so timestamps stay correct across parts.
- Transcripts too long for one LLM call are map-reduced over
  sentence-boundary windows; cited ids are validated against each window and
  the merged result passes the same guards.
- Audio streams from disk end to end. The one whole-file-in-RAM case is the
  diarizer waveform, about 0.23 GB per audio hour, bounded by the upload cap.
- If the server restarts mid-job, the job settles at boot: with a stored
  transcript it stays usable and analysis can be retried, otherwise it fails
  with a clear message instead of spinning forever.

## Offline mode

The target environment may have no internet, so the whole pipeline can run
locally: set both providers to `local` in .env and start with
`docker compose --profile local up`. faster-whisper handles transcription
and an Ollama-served qwen3:8b writes the minutes. First run downloads about
1.6 GB + 5 GB of weights to the named volumes. It is slower on CPU and
weaker on dialect than the cloud path, but it needs no key and makes no
outbound call.

## Ready-made vs built here

| Third-party | Role | License |
| --- | --- | --- |
| FastAPI, Starlette, uvicorn | HTTP API, static serving, ASGI server | MIT / BSD-3 |
| ffmpeg, ffprobe | Conversion, silence detection, splitting, probing | LGPL-2.1, unmodified subprocess |
| Whisper large-v3 via Groq | Cloud transcription; Groq also serves the minutes LLM | MIT model, Groq API |
| pyannote community-1 | Local speaker diarization (gated model) | MIT lib, model has own terms |
| faster-whisper (CTranslate2) | Offline transcription | MIT |
| Ollama + Qwen3 | Offline minutes LLM | MIT / Apache-2.0 |
| python-docx, lxml | DOCX package building | MIT / BSD-3 |
| hijridate | Umm al-Qura Hijri conversion | MIT |
| IBM Plex Sans Arabic | UI typeface, vendored woff2 | OFL 1.1 |

Built in this repository: the recording page and the whole UI, the pipeline
orchestration (parallel transcribe/diarize, skippable stages, soft-fail
analysis), sentence assembly and speaker attribution, the citation and
faithfulness guards, the deterministic date layer, the map-reduce path with
its token budgets, the RTL DOCX builder (schema-ordered OOXML, per-run
direction), and the single Arabic error surface.

## Checks

```bash
ruff format --check .
ruff check .
pytest -q
```

Last run (2026-08-21, this machine): both ruff checks clean, 242 tests pass
in ~24 s with one Starlette deprecation warning. No test touches the
network; all providers are mocked. One manual check before shipping: reload
the page mid-processing and confirm the `#<id>` URL restores the job.

`./scripts/package.sh` zips the tracked tree after refusing any tracked .env
or key material.

## Not done, and known limits

- No demo video was recorded; the quick start above is the walkthrough.
- Transcription is pinned to Arabic. A recording in another language is not
  detected or rejected; it comes back as unusable Arabic-shaped text.
- One meeting at a time is the sizing. Parallel uploads run, but they share
  CPU, RAM, and the free-tier rate limits with no queue.
- The free Groq tier is limited per minute and per day; a burst of analyses
  surfaces as a retryable Arabic error, and re-analysis is one click.
- Diarization holds the full waveform in RAM and needs the gated pyannote
  model accepted on your HF token.
- The prompt comparison in docs/DECISIONS.md is indicative only: one of the
  three clips is not shipped (its license forbids redistribution) and no
  harness re-runs it.
- On a Mac without a system ffmpeg, running outside Docker looks for
  ffmpeg under `~/ffmpeg/bin`. Inside the container this is a no-op.

Why each choice was made, dated: [docs/DECISIONS.md](docs/DECISIONS.md).

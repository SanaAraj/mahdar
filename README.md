# Mahdar

A single-page Arabic meeting recorder that turns a live microphone recording or
an uploaded audio file into a structured, fully-cited meeting summary.

## Where things stand

- **Why each choice was made:** [docs/DECISIONS.md](docs/DECISIONS.md) is the
  dated record of every technical decision in this repository.
- **How to run the checks yourself:** `ruff format --check .`, `ruff check .`,
  `pytest -q`.

Last verified result (2026-08-20, this development machine): `ruff format --check .`
reports 69 files already formatted, `ruff check .` reports all checks passed,
and `pytest -q` reports **228 passed, 1 warning** in ~21 s. The one warning is a
Starlette deprecation notice from the `TestClient` shim, not a test failure.

## Overview

Mahdar runs as one Docker service. The browser page is the whole product: you
record a meeting (or drop in an existing file), and the server produces an
Arabic transcript with sentence-level timestamps, optional speaker separation,
and a minutes document with topics, decisions, and tasks. Every topic,
decision, and task carries the IDs of the exact transcript sentences it rests
on, so nothing in the minutes is a guess.

The user flow, in words:

1. Open the page, press the round record button (or drop an audio file).
2. During recording you get a live level meter, an mm:ss timer, pause, and resume.
3. Stop. The upload shows a progress bar, then the stage list lights up:
   convert, transcribe, diarize, assemble, analyze.
4. On completion you see the audio player pinned to the top, a speaker bar,
   then three sections: meeting minutes, follow-up tasks, full transcript.
5. Click any sentence to seek the player to it. Click a citation chip to jump to
   the source sentence. Click a speaker chip to rename them (and hear a 3-second
   sample of their voice first).
6. Task dates that were said relatively ("tomorrow", "end of the month", a
   Hijri date) are normalized to a Gregorian ISO date with its Hijri match by a
   deterministic local layer, not by the model.
7. From the finished view, export the whole meeting as a JSON document or a
   right-to-left Arabic DOCX minutes file with one click.

## Quick start

```bash
cp .env.example .env
# edit .env: set GROQ_API_KEY (and HF_TOKEN for speaker separation)
docker compose up
```

Then open http://localhost:8100. The only hard requirement is a free Groq API
key from https://console.groq.com. Speaker diarization is optional and needs a
free Hugging Face read token (accept the model terms at
https://huggingface.co/pyannote/speaker-diarization-community-1 first).

The app listens on port **8100**. Edit `ports` in `docker-compose.yml` if you
want a different one.

Jobs and the Hugging Face model cache live on the named Docker volume
`mahdar-data`, so nothing lands on the host you need to clean by hand. To wipe
all stored meetings and models, run `docker compose down -v`.

Recording uses the browser MediaRecorder. Chrome and Edge are supported;
Safari and older Firefox may not support `audio/webm` capture. File upload
works in every modern browser.

### Environment variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GROQ_API_KEY` | yes | (empty) | Groq key for transcription and minutes extraction. |
| `HF_TOKEN` | no | (empty) | Hugging Face read token; enables local pyannote diarization. |
| `GROQ_STT_MODEL` | no | `whisper-large-v3` | Groq speech-to-text model. |
| `GROQ_LLM_MODEL` | no | `openai/gpt-oss-120b` | Groq chat model for minutes. |
| `MAX_UPLOAD_MB` | no | `500` | Upload size cap in megabytes. |
| `DATA_DIR` | no | `/data` | Where job JSON and derived audio are stored. |
| `STT_PROVIDER` / `LLM_PROVIDER` | no | `groq` | Provider selectors: `groq` (cloud, needs `GROQ_API_KEY`) or `local` (offline, needs no key). See Offline mode below. |
| `LOCAL_STT_MODEL` | no | `large-v3-turbo` | Faster-whisper model used when `STT_PROVIDER=local`. |
| `LOCAL_LLM_MODEL` | no | `qwen3:8b` | Ollama model served when `LLM_PROVIDER=local`; pulled by the compose `local` service. |
| `OLLAMA_URL` | no | `http://ollama:11434/v1` | Where the app reaches the local LLM. |

## Offline mode

The app runs fully offline. Diarization was already local; transcription and
analysis each have a local adapter behind the same protocol, and the cloud path
stays byte-for-byte untouched when the selectors are `groq`. Setting both
providers to `local` runs the whole pipeline with no outbound network call and
no key.

Two steps:

```bash
# 1. In .env, set the two provider selectors to local
#    STT_PROVIDER=local
#    LLM_PROVIDER=local

# 2. Bring up the app and the local model server together
docker compose --profile local up
```

The `local` profile starts an Ollama service that pulls `LOCAL_LLM_MODEL` on
first run. Faster-whisper downloads its weights on the first local
transcription.

Be honest about what offline costs before relying on it for an evaluation:

- **First-run downloads are real.** The Whisper weights are about 1.6 GB and
  the local LLM is about 5 GB; both land once on the named volumes and persist.
- **Processing is slower.** The default cloud path is groq-fast; the local path
  runs both models on CPU and is noticeably slower on the same clip.
- **Dialect quality is lower.** The local STT (`large-v3-turbo` at int8) and a
  small local chat model handle Modern Standard Arabic better than the two
  Gulf-dialect clips in `samples/` (the external Egyptian channel is worse
  still); expect fewer and looser
  extractions than the cloud path on dialect-heavy audio.

This mode exists because the end environment may be fully closed, and a
lower-quality path that runs at all counts for more than a higher-quality one
that does not.

## Export

Once a meeting is done, two endpoints hand you the finished product, no
re-processing needed:

- `GET /api/meetings/{id}/export/json` returns the canonical meeting document
  as a `mahdar-{id}.json` attachment.
- `GET /api/meetings/{id}/export/docx` renders the minutes
  (under the `mahdar-data` volume) on demand and returns it as a
  `mahdar-{id}.docx` attachment.

Both are guarded by the same job-id rule as the rest of the API: an unknown
or malformed id is a 404 in Arabic, and internal state (stage bookkeeping,
file paths, errors) never leaves the server.

### JSON export schema

The body is the persisted analysis plus the transcript, trimmed to public
fields. `meta` wraps the identifying facts; `sentences` carry the speaker id
of each line; `analysis` is what the minutes render, and is `null` when
extraction failed or was skipped (transcript and meta still export).

```json
{
  "meta": {
    "id": "c3d4e5f6a7b8",
    "created_at": "2026-08-18T09:41:02",
    "date_gregorian": "2026-08-18",
    "date_hijri": "1448-03-05",
    "duration_s": 761.4
  },
  "speakers": [
    { "id": "SPEAKER_00", "label": "<Arabic speaker label>", "first_start": 0.0 }
  ],
  "sentences": [
    { "id": "s1", "start": 0.35, "end": 3.1, "text": "<Arabic transcript line>", "speaker": "SPEAKER_00" }
  ],
  "analysis": {
    "title": "<Arabic meeting title>",
    "attendees": ["<Arabic attendee name>"],
    "topics": [
      { "title": "<Arabic topic title>", "summary": "<Arabic topic summary>", "segment_ids": ["s1"] }
    ],
    "decisions": [
      { "text": "<Arabic decision text>", "segment_ids": ["s1"] }
    ],
    "directives": [],
    "tasks": [
      {
        "description": "<Arabic task description>",
        "owner": null,
        "due": { "raw": "<Arabic phrase as said>", "gregorian": "2026-08-19", "hijri": "1448-03-06" },
        "priority": null,
        "segment_ids": ["s1"]
      }
    ]
  }
}
```

Field names are stable; spoken-but-unknown values (`owner`, `due`, `priority`)
stay `null` rather than being invented, exactly as the UI shows them.

### DOCX export

The DOCX is a real Arabic right-to-left minutes document, not a flipped
left-to-right file. Every paragraph carries the OOXML bidi flag and right
alignment, the tasks table is `bidiVisual` so its columns lay out
right-to-left, and every stretch of text is split into runs: Arabic runs get
the run-level rtl flag, Latin terms and digits keep their natural order inside
the Arabic flow by not carrying it. Headings and labels come from the same
`strings.py` the API speaks. Fonts are pinned to Arial for both the ascii and
the complex-script slots so the file renders identically on a machine without
our vendored web font. A finished meeting with a failed analysis still
exports: the file then holds the title page, meta, and the full transcript
appendix, plus one Arabic note line instead of the minutes sections.

## Architecture

One Docker service, no database server, no message queue. The backend is
FastAPI; job state is a JSON file per meeting under `DATA_DIR`. The pipeline
runs on background threads inside the same process, and the Dockerfile pins
uvicorn to exactly one worker because that state is in-memory by design.

## Ready-made vs built here

The tables below list the boxed third-party components on the left and what this
repository contributes on the right.

| Third-party component | Role | License |
| --- | --- | --- |
| FastAPI, Starlette, uvicorn | HTTP API, static-file serving, the ASGI server | MIT, BSD-3-Clause, BSD-3-Clause |
| ffmpeg, ffprobe | Conversion to WAV/MP3, silence detection, splitting, duration probing | LGPL-2.1 (GPL with optional modules, used here as an unmodified subprocess) |
| Whisper large-v3 via Groq | The default cloud transcription and the minutes LLM | MIT (Whisper model); Groq serves it over an API |
| pyannote community-1 (via pyannote.audio) | The optional local speaker diarization | MIT (pyannote.audio); the gated community-1 model is subject to its own terms, accepted by the user's HF token |
| faster-whisper (CTranslate2) | The offline local transcription engine | MIT |
| Ollama and Qwen3 | The offline local minutes LLM | MIT (Ollama); Apache-2.0 (Qwen3) |
| python-docx, lxml | Building and serializing the DOCX package | MIT, BSD-3-Clause |
| hijridate | Gregorian-to-Umm-al-Qura Hijri conversion | MIT |
| IBM Plex Sans Arabic | The web UI's Arabic typeface, vendored as woff2 | SIL Open Font License 1.1 |
| Everything else | See below | this repository |

| Built here | Why it had to be built |
| --- | --- |
| The recording UI (record/upload, level meter, timer, pause/resume) and the whole single page | No framework covers RTL Arabic capture with this interaction model out of the box |
| The pipeline orchestration (convert, parallel transcribe/diarize, assemble, analyze) over background threads | The stage model, the parallel pair, and the SKIPPED state are product decisions no library holds |
| Sentence assembly from word-level tokens | Pause/terminator/honorific rules with the 0.75 s / 30-word / 18 s thresholds are specific to this product |
| Speaker overlap assignment and ordering | Maximal-overlap turn attribution with first-appearance speaker numbering is a product rule |
| Citation existence and lexical-overlap grounding guards | The "no item survives without a grounded source sentence" contract does not exist in any dependency |
| Deterministic date normalization (relative + Hijri) | The model says the phrase; the local layer computes the date so a guess is impossible |
| The map-reduce analysis path | Windowing at sentence boundaries, id remapping across windows, and the fuse-on-overlap reduce were built for this transcript shape |
| The DOCX RTL builder | Every paragraph's bidi flag, the bidiVisual tasks table, per-direction runs, and schema-ordered OOXML insertion are all hand-built |
| The unified error system | One exception hierarchy mapped to Arabic copy at the API boundary is the product's contract with the user |

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

| Stage | What it does | Typical duration |
| --- | --- | --- |
| convert | ffmpeg from the upload to 16 kHz mono WAV and 64 kbps mono MP3, all disk to disk. Records the duration. | < 1 s per minute of audio |
| transcribe | Streams the MP3 to Groq whisper-large-v3 for word-level timestamps, using an open file handle. Files over 24 MB are split at silence first. | a few seconds per minute |
| diarize | Runs pyannote community-1 locally when `HF_TOKEN` is set; runs in parallel with transcribe and never blocks it. | roughly real-time on CPU |
| assemble | Builds sentences from words (pause/punctuation/hard limits) and assigns each sentence to a speaker by time overlap. | milliseconds |
| analyze | Sends the transcript to the Groq chat model (or the local LLM when `LLM_PROVIDER=local`) in one pass and validates the JSON against the Analysis schema; a transcript over the prompt budget is map-reduced over sentence-boundary windows and merged by one reduce call. Drops any item whose citations do not resolve, and normalizes dates deterministically. | tens of seconds |

## Audio handling

Memory discipline is a first-class design constraint. No whole audio file ever
sits in process memory unless that is technically unavoidable.

- **Upload** streams the incoming file to disk in fixed-size chunks with a
  running byte count. If the body crosses the cap mid-stream the server answers
  413, deletes the partial file, and stops reading; the whole upload is never
  buffered in RAM. `tests/test_api.py::test_oversized_stream_is_cut_midway`
  proves the cut happens after the first over-cap chunk.
- **Groq transcription** passes an open binary file handle to the httpx
  multipart body, so the request body streams from disk rather than a bytes
  object held in memory.
- **ffmpeg** conversion and splitting are disk-to-disk subprocesses, so no
  decoded audio ever enters the Python process.
- **Serving** uses FastAPI `FileResponse`, which streams from disk and supports
  HTTP range requests for the player.
- **Diarization** is the single intentional exception. pyannote's
  `torchaudio.load` decodes the full waveform into RAM by design: float32 mono
  at 16 kHz is 64,000 bytes per second, about 0.23 GB per hour of audio. This
  cost is documented and bounded by the upload cap, and it only applies when
  `HF_TOKEN` is set. See `docs/DECISIONS.md`.

## Configuration reference

Fixed engineering values (retry counts, timeouts, chunk and size caps, the
sentence thresholds 0.75 s / 30 words / 18 s, the 8,550-token prompt budget,
upload extensions, silence-detection parameters) live in
`backend/app/constants.py`. The frontend mirrors this split in
`frontend/config.js` (poll interval, preview seconds, palette, MIME candidates,
extensions). `backend/app/config.py` holds only env-tunable settings; the
`.env` table above is the full operator-facing surface.

## Testing

The full check is three commands, run from the repo root:

```bash
ruff format --check .
ruff check .
pytest -q
```

On the last run (2026-08-20) these passed clean: `ruff format --check .` ->
69 files already formatted; `ruff check .` -> all checks passed; `pytest -q` ->
228 passed, 1 warning (the Starlette `TestClient` shim deprecation, not a
failure). Re-run `pytest -q` any time for the current count.

The suite covers the sentence segmentation rules (punctuation,
pause, hard word/duration limits, honorifics), the deterministic date layer
(relative, explicit Gregorian, and Hijri with no guessing), speaker assignment
by maximal overlap with first-appearance ordering, citation cleaning with the
overlap faithfulness guard, the audio split-point logic, the Groq STT and LLM
providers against mocked HTTP including Retry-After on 429, the provider
factory and both local-provider adapters against mocked transports (no model
downloads in tests), the upload streaming cap, the full API lifecycle (upload,
parallel stages, degraded no-token mode, soft-fail analysis, rename +
re-analyze, persistence across a registry reload), and the two exports (JSON
schema and DOCX structure via document.xml, with no Word needed). No test makes
a real network call; the Groq, diarization, and local providers are mocked. Run
it yourself with `pytest -q` for the current count.

One check the suite deliberately does not automate: the URL-restore flow.
Record or upload a meeting, watch the URL gain `#<id>`, reload mid-processing
and confirm the stage list resumes, then reload when done and confirm the
finished view renders. Loading a bad or unknown id must land on a clean fresh
state. This needs a live server and a real browser, so it stays a manual
pre-submission check rather than an automated one.

## Delivery

To package the exact tracked tree as it ships, run:

```bash
./scripts/package.sh
```

It aborts if a `.env` file is tracked or any Groq key material (`gsk_`) appears
in the tracked tree, then writes `mahdar.zip`.

## Evaluation notes

This section compares two extraction system prompts against the live key on the two
Gulf-dialect news clips in `samples/` and one Egyptian channel from the local
external set: the
current English-instructions prompt (rules in English, Arabic only as embedded
exemplars and as data) against the retired all-Arabic prompt reconstructed as a
test-only fixture. Each clip was transcribed once, then extracted once under
each prompt with the configured model. Counted per run: the items the citation
or overlap guard drops (lower is better), the one schema-or-Arabic-guard retry,
and whether every returned value stayed Arabic.

| Clip | Sentences | Prompt | Retries | Dropped | All values Arabic |
| --- | --- | --- | --- | --- | --- |
| `news_clip_low_income` | 3 | English | 0 | 0 | yes |
| `news_clip_low_income` | 3 | Arabic | 0 | 0 | yes |
| `news_clip_sports_strategy` | 2 | English | 0 | 0 | yes |
| `news_clip_sports_strategy` | 2 | Arabic | 0 | 0 | yes |
| `egyptian_sports_speaker_a` | 5 | English | 0 | 0 | yes |
| `egyptian_sports_speaker_a` | 5 | Arabic | 0 | 0 | yes |

One honest caveat: these three clips sit well under the prompt budget and came
back clean under both prompts, so neither the guard path nor the merge path was
stressed. The English prompt is kept, for its stronger instruction following,
its portability across a model swap, and because it keeps the codebase's
English-only discipline; on this evidence the two prompts are equivalent.

## Limitations and honest notes

- Speaker diarization holds the full waveform in RAM (about 0.23 GB per hour);
  this is the one intentional whole-file case, bounded by the upload cap.
- Diarization requires a Hugging Face token that has accepted the gated
  pyannote model's terms. Without it, meetings still transcribe and analyze and
  the diarize stage is shown as skipped with a clear note.
- Minutes extraction runs in one pass on a budget-fitting transcript; a
  transcript over the 8,550-token budget is map-reduced over sentence-boundary
  windows rather than failed, and the merged result passes the same citation
  and overlap guards. A transcript so long its per-window summaries themselves
  overflow the reduce budget still fails with an Arabic message asking you to
  split the recording into shorter meetings.
- On macOS hosts without a system ffmpeg, `config.py` looks for the ffmpeg and
  ffprobe binaries under `~/ffmpeg/bin` (the project's documented local
  toolchain) before the converters run. Inside the container ffmpeg is already
  installed and this lookup is a no-op.
- The free Groq tier is rate-limited per minute; a burst of analyses can hit
  the cap, and the pipeline surfaces that as a retryable stage error.

## Status and roadmap

- **Phase 1** record/upload -> Groq transcription -> sentence UI. Done.
- **Phase 2** speaker diarization (pyannote, parallel thread) + renaming. Done.
- **Phase 3** LLM minutes and tasks with per-item citations + date
  normalization (relative + Hijri). Done.
- **Phase 4** DOCX (proper RTL) and JSON export. Done.
- **Phase 5** hardening, retry, long-audio chunking, full tests. Done.
- **Phase 6** README, provider bake-off notes, optional extras. Done.

See `docs/DECISIONS.md` for the dated technical decision log.

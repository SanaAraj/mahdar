# Decisions

A dated log of the choices behind Mahdar's pipeline, in the order they were
made. The housekeeping choices (packaging, fonts, volume layout) are left out
on purpose; what is here is the part that touches the models and the data that
flows around them.

## 2026-08-18: Groq's whisper-large-v3 for transcription

Groq serves Whisper large v3 with word-level timestamps on a free tier big
enough for real use, and the word timing is what makes sentence-level seek
possible later in the UI. The API caps uploads at 25 MB, so anything over
24 MB is split at silence points first and the parts are transcribed with a
running offset. The split offsets advance by the intended window, never by the
re-probed length of the encoded part, because an MP3 that lands a few hundred
milliseconds short would otherwise drag every later timestamp with it.

## 2026-08-18: openai/gpt-oss-120b for the minutes

Groq retired llama-3.3-70b-versatile and qwen/qwen3-32b in June 2026 and
steered accounts to openai/gpt-oss-120b, so that is the default now. A model
id can die between two builds, so the analyze stage checks the /models
listing once per process and, if the configured id is gone, fails with an
Arabic message naming live alternatives instead of hanging on a dead model.

## 2026-08-18: English rules in the prompt, Arabic values out

The extraction system prompt is written in English with a few Arabic
exemplars embedded; every JSON value must come back Arabic while the field
names stay English per the schema. I ran an A/B against the original
all-Arabic prompt on three clips (two Gulf, one Egyptian): six runs, no
retries, nothing dropped, fully Arabic output both ways. On that evidence the
two prompts are equal, and the English one stayed because it follows
instructions harder and survives a model swap. The retired Arabic prompt is
kept as tests/fixture_prompt_arabic.py as the honest record of what was
compared; the app never imports it, and no automated harness re-runs the
comparison.

## 2026-08-18: every extracted item must cite its sentences

The transcript goes in with an [sN] id on each line, and every topic,
decision, and task has to echo the ids it rests on. Two guards then run.
First existence: ids pointing at nothing are trimmed, and an item left with
none is dropped. Second overlap: the item's own wording must share at least
one normalized content token with the sentences it cites, or it goes. That
second guard exists because I watched the model cite perfectly valid ids
while describing things nobody said. Normalization folds the alef and hamza
forms, ta marbuta, diacritics, and tokens under three characters, and is used
only for matching; stored text is never rewritten. An early version checked
only the topic summary and dropped grounded items whose summary happened to
be a paraphrase, so the guard now reads all of an item's content fields
together.

## 2026-08-18: dates are computed by code, never by the model

The model passes back only the phrase as said: "end of week", "after a
month", a Hijri date. A deterministic layer turns that into a Gregorian date
and its Umm al-Qura Hijri counterpart, anchored to the meeting date. The
rules that mattered: "next Thursday" always means next week's (whoever means
the nearest Thursday just says "Thursday"); the Saudi work week ends on
Thursday and the weekend starts Friday, so "end of week" lands on Friday and
"end of work week" on Thursday; "after a month" is a calendar month, clamped
so January 31 plus one month ends at the last day of February rather than the
start of March. A Hijri date spoken without a year is genuinely ambiguous and
comes back empty. Anything the layer cannot match stays null. It does not
guess, and a date the model made up is cleared whenever the raw phrase is
missing.

## 2026-08-18: sentences close on pauses, terminators, and hard limits

A sentence closes when any of these hit: a pause of 0.75 seconds, a
terminator, 30 words, or 18 seconds. The terminators are exactly the four the
spec names: period, the Arabic question mark U+061F, exclamation, and the
Arabic semicolon U+061B. The colon is deliberately not a closer because it
shows up in headings and lists without ending anything, and Arabic honorific
abbreviations that end in a period (the doctor and professor titles) do not
close a sentence either.

## 2026-08-18: diarization is local, optional, and never blocks the text

pyannote community-1 runs on CPU in parallel with transcription, so speakers
never delay the transcript. A missing or rejected Hugging Face token marks
the stage SKIPPED with a fixed Arabic note and the meeting still completes,
with speaker left null on every sentence. The pipeline takes the exclusive
(non-overlapping) diarization output so each sentence maps to exactly one
turn: the largest time overlap wins, ties go to the earlier turn, and
speakers are numbered in order of first appearance. Renaming a speaker later
re-runs the analysis so the minutes pick up the new names. (Later, on
2026-08-20: pyannote's own audio loader broke on this machine, so the 16 kHz
WAV is decoded with a small stdlib reader and handed over as a waveform
instead.)

## 2026-08-18: extraction gets at most two tries

One POST, and at most one corrective retry. A schema-invalid reply gets the
error tail sent back for one more attempt; a schema-valid reply that comes
back in English gets one Arabic-output nudge. The two failure modes share the
single retry slot on purpose, so the request count stays bounded no matter
what the model does. The extractor also asks for include_reasoning=false and
drops the field exactly once if a model rejects it.

## 2026-08-18: 429s are paced, not hammered

The free tier limits tokens per minute, so when a 429 carries a Retry-After
header the shared retry helper sleeps out the window (capped at 70 seconds)
instead of retrying inside it. Without the header it falls back to plain
backoff with a little jitter, so two calls that rate-limit together do not
wake up together.

## 2026-08-18: a fully offline path exists

faster-whisper large-v3-turbo (CPU, int8) and an Ollama-served qwen3:8b sit
behind the same two provider interfaces, selected with STT_PROVIDER=local and
LLM_PROVIDER=local. The local extractor subclasses the cloud one, so the
two-call contract, the Arabic-output guard, the token budgets, and the
map-reduce path all carry over unchanged. The VAD filter is on for local
transcription because Whisper's silence hallucination needs suppressing
wherever the model runs. The costs are stated in the README: about 1.6 GB
plus 5 GB of first-run downloads, slower CPU processing, and weaker dialect
handling. The mode exists because the final environment may have no internet
at all, and a weaker path that runs beats a stronger one that cannot.

## 2026-08-19: long transcripts map-reduce, on measured budgets

The budgets here are measured, not guessed. A 37-minute sample got rejected
by Groq with the payload counted at 9,296 real tokens against an internal
estimate of 4,247; the old 3.5 characters-per-token assumption was off by
about 2.2x for Arabic. The constant is now 1.25. The single-call budget is
8,550 estimated tokens, sized to stay inside the 8K free-tier per-minute
window, and a map window gets 5,000 after subtracting 3,180 of measured
prompt overhead and a 370-token safety margin. Windows never split a
sentence. Windows keep their real sentence ids in the prompt and the model is
told to cite only the ids shown, so before any merge each window's citations
are grounded against that window's own id set: a stray id from another window
is dropped, never remapped. The reduce call sees only the
compact per-window summaries (capped at 60 items), never the transcript, and
near-duplicate items fuse and carry the union of their segment ids. The
merged result passes the same citation, overlap, and date guards as the
single pass. If even the reduce input overflows, the user gets an Arabic
message asking them to split the recording; nothing is truncated silently.

## 2026-08-20: silence hallucinations are filtered, not trusted

A 60-second upload of pure silence came back from Whisper as a confident
sentence with an invented name, the segment marked no_speech_prob 0.70. That
settled it: words belonging to segments above 0.6 on that score are
dropped, and runs of repeated identical sentences (the loop Whisper falls
into on dead air) are collapsed. The silence clip now produces zero sentences
instead of a fake one, and the filter runs in the assemble stage so the cloud
and local paths share it.

## 2026-08-20: window citations are grounded, never remapped

The first map-reduce cut assumed each window's reply renumbered its citations
from s1 and remapped them onto the real ids, while the window prompt showed
the real ids and told the model to cite only those. A compliant model's
later-window citations therefore mapped to nothing and every item it
extracted past the first window was culled by the citation guard. The remap
is gone: windows keep their real sentence ids end to end, and each window's
citations are filtered against that window's own id set, so a foreign id is
dropped instead of being translated onto the wrong line. A regression test
drives a six-window transcript through a mocked compliant model and asserts
the last window's id survives into the merged minutes.

## 2026-08-20: a diarized speaker change closes a sentence

Verified live on a real two-party call: rapid exchanges shorter than the
0.75-second pause threshold landed in one sentence, which was then credited
wholesale to whichever speaker held the larger overlap. A diarized turn
change is now a hard sentence boundary beside the pause, the terminators,
and the word and duration limits. When diarization was skipped or failed
there are no turns, and segmentation is exactly what it was before.

## 2026-08-20: interrupted jobs settle at boot

A state file persisted mid-run used to reload as running forever, leaving an
endless stage spinner with no way out (observed on a real job after a dev
restart). On registry load, an in-flight job that already stored its
transcript becomes done with a retryable analyze error note, mirroring the
runner's soft-fail; a job interrupted before any transcript becomes failed
with the retry message. Deliberately no auto-resume: replaying half a run
against half-written artifacts risks silently mixing stale and fresh output,
and a clean retry is cheap.

## 2026-08-20: minutes and task rows seek by their first cited sentence

The per-item citation chips were removed with the s-id listing because the
chips read as a debugging surface, but that also removed the task sheet's
click-any-item-to-jump behavior. The row itself is now the control: a topic,
decision, directive, or task whose citation resolves seeks the player to its
first cited sentence and highlights it exactly as a transcript row does. A
row whose citations do not resolve gets none of the button affordances, so a
dead row is visibly plain rather than silently ignoring clicks.

## 2026-08-21: the reduce reply is anchored and key-repaired, never guessed

On long meetings the reduce call occasionally returned JSON the schema
rejected: uppercase field names, observed live as four attempts before a
valid reply on a 37.5-minute recording. Root cause: the reduce prompt was the
only extraction prompt that never showed the JSON schema, while its input
blocks are labeled with uppercase markers (TITLE, TOPIC, DECISION), so the
model mirrored the only field names it ever saw. Two changes, both
deterministic. First, the reduce prompt now carries the same schema example
as the extraction prompt plus an explicit rule that the uppercase markers
label the input and are never JSON keys; the reduce token budget was
re-derived for the larger prompt (overhead 1360 to 1740, budget 6820 to
6440). Second, a key-case repair runs before every validation: a key whose
lowercase form is a known schema field is renamed, only when the exact field
is not already present, and values are never touched, so a reply that was
correct apart from key casing passes on the first call instead of spending
the single correction retry. The transcript was never affected by this
failure; only the extracted minutes were.

## 2026-08-21: one uvicorn worker, background threads, JSON on disk

Recorded late because it is the most likely question about this architecture:
where is the database, the queue, the second worker? Nowhere, on purpose.
Mahdar is sized as a single-meeting tool: one person records one meeting and
reads one set of minutes, so concurrency is an occasional overlap, not a load
profile. Job state lives in an in-process registry with the pipeline on
background threads, and every meeting persists as JSON files under /data, so
uvicorn must run exactly one worker: a second process would hold a second
registry and the two would race on the same state files. What a database and
a queue would normally buy is covered at this scale by cheaper mechanisms
already in place: crash recovery by the boot settle (an interrupted job
reloads as failed or retryable, never as a zombie), transient failures by the
bounded retry helpers, and inspectability by the state being plain JSON a
person can read and back up with cp. Redis, Celery, or a SQL server would
each add one more stateful service to the one-command compose file and an
operational surface this scope does not need. If this were productized for
real concurrency, the cut line is already drawn: job state moves from the
in-process registry to a shared store, stage execution moves from threads to
queue workers, and the HTTP tier then scales horizontally behind them. The
stages already communicate only through persisted artifacts (state.json,
words.json, turns.json), so that migration replaces the registry, not the
pipeline.

## 2026-08-21: model selection: what shipped and what was scouted

Groq's whisper-large-v3 stays the shipped transcription default for two
concrete reasons: an evaluator can create a free key in minutes and run the
whole pipeline the same day, and the API returns word-level timestamps, which
sentence-level seek, citation grounding, and the silence filter are all built
on; an STT service returning plain text would disable all three. During
research, CohereLabs/cohere-transcribe-arabic-07-2026, an Arabic-specialized
STT model released in July 2026, was evaluated on the HUMAIN Fuse sovereign
platform. It was not integrated into this codebase, and nothing here depends
on it. The provider factory is the designed upgrade seam for that class of
deployment: a closed government environment would put a sovereign router
(Fuse or similar) or the fully offline path (see the 2026-08-18 offline
entry) behind the same two provider interfaces, without touching the
pipeline.

## 2026-08-21: the reduce step can still return an empty reply

The uppercase-keys reduce failure was fixed deterministically (schema anchor
plus key-case repair, above). A second failure mode remains open: on long
meetings, smaller reasoning models can spend the whole completion budget
(MAX_COMPLETION_TOKENS, 4000) on internal reasoning and return an empty
reduce reply. The extractor asks for include_reasoning=false, but models
that reason internally consume those tokens either way, and an empty reply
gives the key-case repair and the corrective retry nothing to work on. This
is mitigated, not eliminated: the completion budget carries headroom well
past any minutes object seen in testing, the analyze stage soft-fails so the
transcript and speakers stay intact and the job stays done, and re-analysis
is one click in the UI. Eliminating it outright would mean raising the
completion budget against the free-tier tokens-per-minute window or pinning
the reduce call to a larger model; both cost more than the retry does.
Recorded so the empty-reply path is not mistaken for a regression of the
fixed one.

## 2026-08-22: monorepo on Turborepo, bun for JS, uv for Python

The refactor replaces the single backend + hand-rolled frontend with two typed
packages under apps/: api (FastAPI on uv) and web (TanStack Start on bun) — a
single root lockfile, one test runner (`turbo run test`), and one tree-wide
`docker compose up` via the Caddy proxy. The Python tree moved from
`backend/app/{core,api,providers,processing}` to a feature-first
`apps/api/app/{features/{meetings,transcription,diarization,analysis,export},shared,pipeline,api}`.
The uv lock pins the existing torch 2.11.0 CPU / torchaudio 2.11.0 /
torchcodec 0.11.1 combo exactly as it was live before the move (the
`requirements.txt` baseline of 114 names); any small drift in
huggingface-hub/idna/lxml/narwhals/protobuf versions reflects uv's resolver
and is documented in the report. onnxruntime stays a linux-only override
because faster-whisper imports it lazily and macOS 12 lacks the wheel.

## 2026-08-22: Phase B hardening

- Slowapi limits per route (upload 3/min·20/h, analyze 5/min·30/h,
  status polls 120/min, renames 30/min, docx 10/min, json/audio 30/min);
  health stays exempt.
- Container sniffing on the first chunk (WebM EBML, OggS, RIFF/WAVE, ID3,
  MP3 frame-sync, ftyp) rejects a mislabeled binary earlier than ffmpeg.
- The pipeline runs through a `BoundedSemaphore(max_active_jobs)`; one more
  upload while busy gets 503 + Retry-After: 30 + Arabic copy. Production
  default is 3, tests raise to 8 via the MAX_ACTIVE_JOBS env var.
- CORS is opt-in via CORS_ORIGINS; the production deployment is single-origin
  behind Caddy, so the default is empty.

## 2026-08-22: single-origin via Caddy in front of api and web

The old app served the static frontend from the same Starlette process;
that made a /api/* prefix and a /api/health check easy but baked the React
app into the Python image. The new layout runs Caddy on the public :8100,
serving /api/* to `api:8000` and everything else to `web:3000`. Dev
mirrors this through apps/web's own server splat route (`/api/$`) that
proxies /api/* to http://localhost:8100 — TanStack Start's vite dev server
proxy does not honor the appbar catch-all, so the in-app route is the
reliable path (verified across Start releases as of 2026-08-22).

## 2026-08-22: tanstack start pinned to 1.168.48 with vite 7

`@tanstack/react-start@1.168.48` + `@tanstack/react-router@1.170.31` after
the 2026-05 supply-chain advisory (1.167.68/1.167.71 were withdrawn) and the
vite-8 SSR registration regression (issue TanStack/router#7614). Bun is
1.3.14 (not 1.4 — lockfile-v2 hash compatibility with turbo prune).

## 2026-08-22: shadcn on radix primitives, RTL via DirectionProvider

shadcn 4.19 defaults to Base UI primitives since 2026-07; this repo pins
radix to keep the documented `@radix-ui/react-direction` DirectionProvider
and because the Figma-derived design tokens map 1:1 onto the legacy
styles.css variants. `html dir="rtl" lang="ar"` from the root route;
logical Tailwind utilities (ps/pe/ms/me) for all spacing.

## 2026-08-22: APIs keep the existing error shape

Every error body is {"error_ar", "code", "detail"} where detail mirrors the
Arabic string (older clients read it). New keys added in Phase B:
`upload.bad_signature`, `rate.limited`, `server.busy`.

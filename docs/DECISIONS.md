# Mahdar technical decisions

> Current architecture only. This is a decision record, not a development diary.

Mahdar's first version was developed locally before its Git history was created. No
complete GitHub project or ready-made meeting-minutes application was imported. The
frameworks, models, services, and UI primitives used by the project are listed in
the README together with the product-specific work built around them. Each decision
below records the context, the chosen approach, and the remaining trade-off.

## Decision index

| ID | Decision |
| --- | --- |
| D1 | [Inference providers](#d1-inference-providers) |
| D2 | [Speaker diarization](#d2-speaker-diarization) |
| D3 | [Timestamped sentences](#d3-timestamped-sentences) |
| D4 | [Evidence-grounded minutes](#d4-evidence-grounded-minutes) |
| D5 | [Deterministic date handling](#d5-deterministic-date-handling) |
| D6 | [Long recordings and transcripts](#d6-long-recordings-and-transcripts) |
| D7 | [State and concurrency](#d7-state-and-concurrency) |
| D8 | [Web and API deployment](#d8-web-and-api-deployment) |
| D9 | [Failure handling](#d9-failure-handling) |
| D10 | [Reviewed exports](#d10-reviewed-exports) |

## D1. Inference providers

**Context.** The main path needs good Arabic transcription, word timestamps, and a
setup an evaluator can run without a GPU. It should also have a path that does not
depend on a hosted inference provider.

**Decision.** Groq is the default provider for both STT and minutes extraction,
using `whisper-large-v3` and `openai/gpt-oss-120b`. Cohere Transcribe Arabic is an
optional STT provider for comparing Arabic transcript quality while the LLM remains
on Groq. Its API path was validated with Arabic recordings. Because Cohere
returns text without timestamps, Mahdar distributes words deterministically across
each audio chunk to satisfy the existing pipeline contract. The same interfaces
also support faster-whisper `large-v3-turbo` on CPU and a configurable
Ollama-hosted model, defaulting to `qwen3:8b`. That local path is implemented and
covered by mocked tests, but it has not been run end to end with real local models.

**Trade-off.** Hosted providers avoid local model setup, but send audio and
transcript context to external services. Cohere is optimized for Arabic dialects
and code-switching, but its estimated word timings reduce seeking and speaker
alignment precision, so Groq remains the default. The local path is intended to
keep inference local after model download, but its real startup behavior, CPU
performance, storage use, and output quality have not yet been verified. None of
these models was trained or fine-tuned here.

## D2. Speaker diarization

**Context.** Speaker labels make the transcript more useful, but diarization is
CPU-heavy and the pyannote model requires separate Hugging Face access. A missing
token should not make the whole meeting unusable.

**Decision.** `pyannote/speaker-diarization-community-1` runs locally on CPU at the
same time as transcription. If it cannot load, its stage is marked as skipped and
the text pipeline continues. Each sentence is assigned to the turn with the largest
time overlap, and speakers are numbered by first appearance. A speaker change also
closes the current sentence so short exchanges are not credited to one person.

**Trade-off.** This keeps transcription available and avoids another cloud service,
but diarization can take close to the recording duration on CPU. Overlapping speech,
noise, and similar voices can still produce incorrect boundaries. Renaming remains
available so the user can correct labels before exporting.

## D3. Timestamped sentences

**Context.** Raw STT words are too small for reading and raw paragraphs are too
large for accurate playback, speaker assignment, and source references.

**Decision.** Words are assembled into sentences using punctuation, a 0.75-second
pause, a speaker change, a 30-word limit, or an 18-second limit. Every sentence has
a stable identifier and start/end timestamps. The transcript, speaker mapping,
minutes citations, audio seeking, and exports all use that same unit.

**Trade-off.** These rules are deterministic and testable, but they remain
heuristics. Unusual punctuation or very rapid speech may split a sentence earlier
or later than a human editor would.

## D4. Evidence-grounded minutes

**Context.** A well-written summary is not useful if it introduces a decision or
task that nobody said.

**Decision.** The LLM must return source sentence IDs for each topic, decision,
directive, and task. Unknown citations are removed. An item with no valid citation,
or no meaningful normalized text overlap with its cited sentences, is dropped.
Clicking a supported minutes item seeks to its first source sentence in the audio.

**Trade-off.** This favors precision over completeness. A valid but heavily
paraphrased item can be removed by the overlap guard. That is safer than presenting
an unsupported action as meeting fact.

## D5. Deterministic date handling

**Context.** Meeting tasks often use relative Arabic dates such as "next Thursday"
or "end of the month". Letting the model calculate them makes the result depend on
prompt interpretation and can create dates that were never stated.

**Decision.** The model returns only the spoken date phrase. A deterministic layer
resolves supported absolute, relative, Gregorian, and Hijri expressions against the
meeting date, then produces both calendar values. Unsupported or ambiguous phrases
remain empty instead of being guessed.

**Trade-off.** The rule set is explainable and testable, but it cannot understand
every informal phrasing. Extending coverage requires adding a rule and its tests.

## D6. Long recordings and transcripts

**Context.** Hosted providers impose audio-size and token limits. Silently
truncating a long meeting would create a complete-looking but incomplete record.

**Decision.** Audio above the STT request limit is split near silence, with offsets
carried into the final word timestamps. Long transcripts are divided only at
sentence boundaries. Each window is analyzed with its real sentence IDs, then a
reduce step merges the compact results. The merged output passes through the same
citation and date checks as a normal meeting.

**Trade-off.** Long meetings require more calls, take longer, and are more exposed
to provider rate limits. If the reduce input cannot fit safely, the application asks
for a shorter recording instead of truncating content.

## D7. State and concurrency

**Context.** This assignment needs a simple one-command system, not a distributed
job platform. Adding a database, broker, and worker pool would increase setup and
failure modes without improving the intended single-user workflow.

**Decision.** One Uvicorn process owns an in-memory registry and runs pipelines on
background threads. Each meeting also persists its state and artifacts under
`/data`. A bounded semaphore limits active pipelines, and interrupted states are
settled on startup instead of remaining stuck as running.

**Trade-off.** Plain files are easy to inspect and back up, but the HTTP service
cannot scale horizontally in this form. A production multi-user version would move
job state to a shared database and execution to queue workers while keeping the
existing pipeline stages.

## D8. Web and API deployment

**Context.** The React application and Python pipeline have different build and
runtime needs, while the user should still open one address and avoid cross-origin
setup.

**Decision.** The monorepo keeps a feature-based FastAPI package and a feature-based
React/TanStack Start package. Caddy exposes port `8100`, routes `/api/*` to FastAPI,
and routes the remaining requests to the web service. Docker Compose starts the
complete topology. CORS is disabled by default because production traffic is
same-origin.

**Trade-off.** Three containers are slightly heavier than serving static files from
Python, but they keep frontend and backend builds independent and make the routing
boundary explicit.

## D9. Failure handling

**Context.** Audio processing and model APIs fail in different ways: invalid media,
rate limits, missing keys, unavailable models, malformed JSON, and interrupted
jobs. A generic server error gives the user no useful next step.

**Decision.** Uploads are limited by size, extension, and file signature. Expensive
routes have rate limits and active-job limits. Provider calls use bounded retries
and respect `Retry-After`. LLM responses get one corrective attempt when the schema
or Arabic-output contract fails. Errors exposed to the UI use stable codes and
Arabic messages. Analysis failures are soft failures, leaving the transcript and
speaker result available for review and retry.

**Trade-off.** Bounded retries may stop before a temporary provider problem clears,
but they keep request cost and waiting time predictable. Preserving partial output
is more useful than failing the complete meeting after transcription succeeds.

## D10. Reviewed exports

**Context.** The exported document should match what the user reviewed, including
renamed speakers and normalized dates, and it must render correctly in Arabic.

**Decision.** JSON and DOCX are generated from the persisted meeting model only
after processing completes. DOCX generation explicitly applies RTL paragraph,
table, and run settings and includes the transcript. Renaming a speaker triggers
minutes re-analysis before exports become available again.

**Trade-off.** The export code is more detailed than a plain document template, but
the result is reproducible and does not depend on office software being installed
on the server.

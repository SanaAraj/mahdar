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
kept as tests/fixture_prompt_arabic.py so the comparison stays repeatable;
the app never imports it.

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
sentence. Because the model numbers each window from s1, the per-window
results are remapped to the real sentence ids before any merge, otherwise
window two would credit window one's lines. The reduce call sees only the
compact per-window summaries (capped at 60 items), never the transcript, and
near-duplicate items fuse and carry the union of their segment ids. The
merged result passes the same citation, overlap, and date guards as the
single pass. If even the reduce input overflows, the user gets an Arabic
message asking them to split the recording; nothing is truncated silently.

## 2026-08-20: silence hallucinations are filtered, not trusted

A 60-second upload of pure silence came back from Whisper as a confident
sentence with an invented name, the segment marked no_speech_prob 0.70. That
settled it: words belonging to segments at or above 0.6 on that score are
dropped, and runs of repeated identical sentences (the loop Whisper falls
into on dead air) are collapsed. The silence clip now produces zero sentences
instead of a fake one, and the filter runs in the assemble stage so the cloud
and local paths share it.

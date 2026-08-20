# samples/

This folder is for local evaluation only. Its contents are never committed to
version control and never redistributed with the project.

## What is here

`samples/external/` is gitignored. It holds short clips used to judge
transcription, diarization, and analysis quality against real speech. Nothing
in this directory ships with the repository.

## Provenance and licensing

The current external set was drawn from two corpora for evaluation and is kept
out of git:

- Egyptian_Arabic_Conversational_Speech_Corpus (Beijing Magic Data Technology
  Co., Ltd.). Two near-telephone conversational channels of the same call,
  trimmed to 90 seconds at a content-rich offset. Licensed for personal,
  non-commercial use only; no part may be distributed or reproduced.
- A small set of Gulf-dialect clips from `~/Downloads/AR` (with human reference
  transcripts, kept beside each derived clip as `*.reference.txt` for
  accuracy comparison).
- `meeting_21.m4a` from `~/Downloads/21.m4a`, a recorded online meeting trimmed
  to a 90-second highlight for a content-rich analysis read.

Because these clips are licensed for evaluation and not for redistribution,
the folder is excluded by `.gitignore` and must never be committed.

## Dropping in your own files

Place any `webm`, `ogg`, `wav`, `mp3`, `m4a`, or `mp4` clip in
`samples/external/`. To judge the pipeline against it, upload the clip in the
running app (or point a local evaluation run at the folder). There is no
required naming scheme; keep clips short enough to fit within the LLM prompt
budget (under a few hundred transcript sentences).

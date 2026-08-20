# samples/

Two short Gulf-dialect news clips ship with the repository, each beside a
human reference transcript (`*.reference.txt`) for accuracy comparison:

- `news_clip_low_income.mp3` (14 s): a commentator on subsidy reform and
  low-income households.
- `news_clip_sports_strategy.mp3` (15 s): a commentator on team selection
  strategy across a tournament.

Upload either one in the running app, or export a meeting and diff the
transcript against the reference file.

## External-only clips

`samples/external/` is gitignored and never redistributed. It holds extra
evaluation clips that must stay local: two channels of an Egyptian telephone
conversation from the Egyptian_Arabic_Conversational_Speech_Corpus (licensed
for personal, non-commercial use; no distribution), and one recorded online
meeting trimmed to a 90-second highlight. Drop any extra `webm`, `ogg`,
`wav`, `mp3`, `m4a`, or `mp4` clip in there to try it locally; keep clips
short enough to fit within the LLM prompt budget.

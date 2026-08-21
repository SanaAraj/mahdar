"""Public pipeline surface: owns the providers and the five stage bodies.

All orchestration length and locking detail lives in core/runner.py; the
analysis-stage helpers live in core/analysis.py. This module only knows how to
run one stage of one job against the providers it was built with.
"""

import logging
import threading

from app.features.analysis import service as analysis
from app.features.transcription import cleanup
from app.features.transcription.sentences import words_to_sentences
from app.features.transcription.speakers import assign_speakers, build_speakers
from app.pipeline.runner import StageRunner
from app.pipeline.stagekit import job_log
from app.shared import audio
from app.shared.errors import (
    AnalysisError,
    AudioError,
    DiarizationError,
)
from app.shared.jobs import JobRegistry
from app.shared.protocols import Diarizer, MinutesExtractor, Transcriber

log = logging.getLogger(__name__)

# Re-exported for tests that exercise the date layer off the model.
apply_meeting_task_dates = analysis.apply_meeting_task_dates


class Pipeline:
    """Coordinates convert, parallel transcribe/diarize, assemble, and analyze."""

    def __init__(
        self,
        registry: JobRegistry,
        transcriber: Transcriber,
        diarizer: Diarizer | None = None,
        extractor: MinutesExtractor | None = None,
    ) -> None:
        self._registry = registry
        self._transcriber = transcriber
        self._diarizer = diarizer
        self._extractor = extractor

    def start(self, job_id: str) -> None:
        threading.Thread(target=self.run, args=(job_id,), daemon=True).start()

    def start_analysis(self, job_id: str) -> None:
        """Re-run only the analysis stage on the stored transcript."""
        threading.Thread(target=self.run_analysis, args=(job_id,), daemon=True).start()

    def run(self, job_id: str) -> None:
        if self._registry.get(job_id) is None:
            job_log(log, job_id).error("pipeline started for unknown job")
            return
        StageRunner(self._registry, job_id, self._map(job_id)).run_full()

    def run_analysis(self, job_id: str) -> None:
        StageRunner(self._registry, job_id, self._map(job_id)).run_analysis()

    # ---- the five stages ----

    def _convert(self, job_id: str) -> None:
        job_dir = self._registry.job_dir(job_id)
        originals = sorted(job_dir.glob("original.*"))
        if not originals:
            raise AudioError("audio.corrupt", "original file missing")
        source = originals[0]
        audio.to_wav16k_mono(source, job_dir / "audio.wav")
        audio.to_mp3_mono_64k(source, job_dir / "audio.mp3")
        duration = audio.probe_duration(job_dir / "audio.wav")
        with self._registry.locked(job_id) as current:
            if current is not None:
                current.duration_s = round(duration, 3)

    def _transcribe(self, job_id: str) -> None:
        job_dir = self._registry.job_dir(job_id)
        words = self._transcriber.transcribe(job_dir / "audio.wav", job_dir / "audio.mp3")
        analysis.write_models(job_dir / "words.json", words)

    def _diarize(self, job_id: str) -> None:
        if self._diarizer is None:
            raise DiarizationError("diarize.skipped", "no HF_TOKEN")
        job_dir = self._registry.job_dir(job_id)
        turns = self._diarizer.diarize(job_dir / "audio.wav")
        analysis.write_models(job_dir / "turns.json", turns)

    def _assemble(self, job_id: str) -> None:
        job_dir = self._registry.job_dir(job_id)
        words = cleanup.filter_no_speech_words(analysis.read_words(job_dir))
        turns = analysis.read_turns(job_dir)
        sentences = cleanup.collapse_repeated_sentences(
            assign_speakers(words_to_sentences(words, turns), turns)
        )
        with self._registry.locked(job_id) as current:
            if current is not None:
                # Read the current labels inside the lock so a renaming in flight
                # is not lost by a stale read taken before the lock.
                labels = {sp.id: sp.label for sp in current.speakers}
                current.sentences = sentences
                current.speakers = build_speakers(turns, labels)

    def _analyze(self, job_id: str) -> None:
        if self._extractor is None:
            raise AnalysisError("analysis.failed", "no extractor configured")
        with self._registry.locked(job_id) as current:
            if current is None:
                return
            sentences = list(current.sentences)
            speakers = list(current.speakers)
            created_at = current.created_at
            duration_s = current.duration_s
        if not sentences:
            raise AnalysisError("analysis.transcript_missing", "no sentences stored")
        meta = analysis.build_meeting_meta(created_at, duration_s)
        anchor = analysis.anchor_date_of(created_at)
        self._finish_analysis(job_id, sentences, speakers, meta, anchor)

    def _finish_analysis(self, job_id, sentences, speakers, meta, anchor) -> None:
        result = self._extractor.extract(meta, sentences, speakers, job_id=job_id)
        result, dropped = analysis.clean_citations(result, sentences)
        if dropped:
            job_log(log, job_id).info("dropped %d items without valid citations", dropped)
        analysis.apply_meeting_task_dates(result, anchor)
        with self._registry.locked(job_id) as current:
            if current is not None:
                current.analysis = result
                current.date_gregorian = meta.date_gregorian
                current.date_hijri = meta.date_hijri

    def _map(self, job_id: str):
        return {
            "convert": lambda: self._convert(job_id),
            "transcribe": lambda: self._transcribe(job_id),
            "diarize": lambda: self._diarize(job_id),
            "assemble": lambda: self._assemble(job_id),
            "analyze": lambda: self._analyze(job_id),
        }

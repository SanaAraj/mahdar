import type { Sentence } from "@/lib/schemas";

export interface SentenceRun {
  speakerId: string | null;
  sentences: Sentence[];
  start: number;
  end: number;
}

export function groupSentenceRuns(sentences: Sentence[]): SentenceRun[] {
  const runs: SentenceRun[] = [];
  for (const sentence of sentences) {
    const speakerId = sentence.speaker ?? null;
    const current = runs[runs.length - 1];
    if (current && current.speakerId === speakerId) {
      current.sentences.push(sentence);
      current.end = sentence.end;
    } else {
      runs.push({ speakerId, sentences: [sentence], start: sentence.start, end: sentence.end });
    }
  }
  return runs;
}

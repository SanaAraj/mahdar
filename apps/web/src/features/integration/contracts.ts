import type { ComponentType, ReactNode } from "react";

import type { Decision, Directive, MeetingJob, Sentence, Speaker, TaskItem, Topic } from "@/lib/schemas";

export interface RecordIdleLabels {
  title: string;
  subtitle: string;
  recordHint: string;
  recordAriaLabel: string;
  orDivider: string;
  uploadZoneLabel: string;
  uploadFormats: string;
}

export interface RecordIdleProps {
  labels: RecordIdleLabels;
  isSupported: boolean;
  onStartRecording: () => void;
  onFilePicked: (file: File) => void;
  onFileRejected: (reasonKey: "invalidFile" | "fileTooLarge") => void;
}

export interface PlayerApi {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  errorAr: string | null;
  toggle: () => void;
  seekTo: (t: number) => void;
  play: () => void;
  pause: () => void;
  seekToSentence: (id: string) => boolean;
}

export interface PlayerProviderProps {
  meetingId: string;
  sentences: Sentence[];
  children: ReactNode;
}

export interface SpeakersBarProps {
  meetingId: string;
  speakers: Speaker[];
  sentences?: Sentence[];
  player?: PlayerApi | null;
  onSpeakerSelected?: (speaker: Speaker) => void;
}

export interface SpeakerTagProps {
  speaker: Speaker;
  className?: string;
}

export interface SentenceListProps {
  job: MeetingJob;
  onSeek: (sentenceId: string) => unknown;
  activeSentenceId?: string;
}

export interface MinutesSectionsProps {
  topics: Topic[];
  decisions: Decision[];
  directives: Directive[];
  startSeconds: Readonly<Record<string, number>>;
  onSeek: (sentenceId: string) => unknown;
}

export interface TasksTableProps {
  tasks: TaskItem[];
  onSeek: (sentenceId: string) => unknown;
}

export interface RecordingFeature {
  RecordIdle: ComponentType<RecordIdleProps>;
}

export interface PlayerFeature {
  PlayerProvider: ComponentType<PlayerProviderProps>;
  usePlayer: () => PlayerApi;
}

export interface SpeakersFeature {
  SpeakersBar: ComponentType<SpeakersBarProps>;
  SpeakerTag: ComponentType<SpeakerTagProps>;
}

export interface TranscriptFeature {
  SentenceList: ComponentType<SentenceListProps>;
}

export interface MinutesFeature {
  MinutesSections: ComponentType<MinutesSectionsProps>;
}

export interface TasksFeature {
  TasksTable: ComponentType<TasksTableProps>;
}

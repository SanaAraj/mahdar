export const POLL_INTERVAL_MS = 2000;
export const RECORD_TICK_MS = 1000;
export const TIMER_TICK_MS = 1000;
export const PREVIEW_SECONDS = 3;
export const MAX_LABEL_LENGTH = 40;
export const CHIP_ERROR_MS = 3200;

export const LEVEL_SENSITIVITY = 3;
export const ANALYSER_FFT_SIZE = 512;

const BYTES_PER_MB = 1024 * 1024;
export const MAX_UPLOAD_MB = 500;
export const BYTES_PER_UPLOAD_MB = MAX_UPLOAD_MB * BYTES_PER_MB;

export const ALLOWED_EXTENSIONS = ["webm", "ogg", "wav", "mp3", "m4a", "mp4"] as const;

export const JOB_ID_RE = /^[0-9a-f]{12}$/;

export const MIME_CANDIDATES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg;codecs=opus",
] as const;

export type SpeakerColor = { bg: string; ink: string; ring: string };

export const SPEAKER_PALETTE: readonly SpeakerColor[] = [
  { bg: "#dbe9dd", ink: "#1d5a24", ring: "#14691b" },
  { bg: "#d8e4ec", ink: "#1d4e6b", ring: "#2c6e91" },
  { bg: "#eee2d4", ink: "#6b4a1d", ring: "#8a5a26" },
  { bg: "#e6dcec", ink: "#4d2a63", ring: "#6b3f86" },
  { bg: "#ecdede", ink: "#6b2323", ring: "#8a3535" },
  { bg: "#dde8e3", ink: "#1d544a", ring: "#2a7266" },
  { bg: "#e7e4d3", ink: "#535124", ring: "#6f6c2f" },
  { bg: "#e0dfe4", ink: "#3c3b52", ring: "#54516e" },
];

export function speakerColor(id: string): SpeakerColor {
  let hash = 0;
  for (const ch of id) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return SPEAKER_PALETTE[hash % SPEAKER_PALETTE.length];
}

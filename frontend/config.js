// Fixed frontend engineering values, mirroring backend/app/constants.py.
// Only env-free, behavior-affecting numbers, sets, and the palette live here.

export const POLL_INTERVAL_MS = 2000; // how often the UI polls the job while processing
export const RECORD_TICK_MS = 1000; // MediaRecorder timeslice, one chunk per second
export const TIMER_TICK_MS = 1000; // on-screen mm:ss timer cadence
export const PREVIEW_SECONDS = 3; // speaker-recognition sample length from first_start
export const MAX_LABEL_LENGTH = 40; // speaker label cap, matches the server rule
export const CHIP_ERROR_MS = 3200; // how long a rename error stays on its chip

// Recording meter feedback.
export const LEVEL_SENSITIVITY = 3; // RMS multiplier that keeps normal speech in range
export const ANALYSER_FFT_SIZE = 512; // analyser window; one frame of samples

const BYTES_PER_MB = 1024 * 1024;
// Client-side upload pre-check, a courtesy before the request starts; the
// server cap (MAX_UPLOAD_MB, default 500) stays the authoritative rule and can
// be tuned lower by the operator. Kept in sync with the server default.
export const MAX_UPLOAD_MB = 500;
export const BYTES_PER_UPLOAD_MB = MAX_UPLOAD_MB * BYTES_PER_MB;

// File extensions the page accepts before the server confirms them.
export const ALLOWED_EXTENSIONS = ["webm", "ogg", "wav", "mp3", "m4a", "mp4"];

// A meeting id the page carries in location.hash so a reload restores the
// running or finished job; matches the server's 12-lowercase-hex id shape.
export const JOB_ID_RE = /^[0-9a-f]{12}$/;

// Preferred recording containers, in order, first supported wins.
export const MIME_CANDIDATES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg;codecs=opus",
];

// Muted 8-chip palette with enough contrast on the light background; the same
// speaker id always hashes to the same chip color across the page.
export const SPEAKER_PALETTE = [
  { bg: "#dbe9dd", ink: "#1d5a24", ring: "#14691b" }, // green (app accent)
  { bg: "#d8e4ec", ink: "#1d4e6b", ring: "#2c6e91" }, // slate blue
  { bg: "#eee2d4", ink: "#6b4a1d", ring: "#8a5a26" }, // sand
  { bg: "#e6dcec", ink: "#4d2a63", ring: "#6b3f86" }, // muted violet
  { bg: "#ecdede", ink: "#6b2323", ring: "#8a3535" }, // muted maroon
  { bg: "#dde8e3", ink: "#1d544a", ring: "#2a7266" }, // teal green
  { bg: "#e7e4d3", ink: "#535124", ring: "#6f6c2f" }, // olive
  { bg: "#e0dfe4", ink: "#3c3b52", ring: "#54516e" }, // blue grey
];

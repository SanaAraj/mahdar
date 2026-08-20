import {
  ANALYSER_FFT_SIZE,
  LEVEL_SENSITIVITY,
  MIME_CANDIDATES,
  RECORD_TICK_MS,
} from "./config.js";
import { STRINGS } from "./strings.js";

export class MeetingRecorder {
  constructor() {
    this.mediaRecorder = null;
    this.chunks = [];
    this.stream = null;
    this.audioContext = null;
    this.analyser = null;
    this.levelData = null;
    this.rafId = null;
    this.onLevel = null;
    this.paused = false;
  }

  supported() {
    return Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder);
  }

  pickMime() {
    return MIME_CANDIDATES.find((m) => MediaRecorder.isTypeSupported(m)) || "";
  }

  async start() {
    if (!this.supported()) {
      throw new Error(STRINGS.micUnsupported);
    }
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      throw new Error(STRINGS.micDenied);
    }
    this.stream = stream;
    this.chunks = [];
    this.paused = false;
    const mime = this.pickMime();
    const options = mime ? { mimeType: mime } : {};
    this.mediaRecorder = new MediaRecorder(stream, options);
    this.mediaRecorder.addEventListener("dataavailable", (e) => {
      if (e.data && e.data.size > 0) this.chunks.push(e.data);
    });
    this._setupMeter(stream);
    this.mediaRecorder.start(RECORD_TICK_MS);
  }

  _setupMeter(stream) {
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = this.audioContext.createMediaStreamSource(stream);
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = ANALYSER_FFT_SIZE;
    source.connect(this.analyser);
    this.levelData = new Float32Array(this.analyser.fftSize);
    const tick = () => {
      if (!this.analyser) return;
      this.analyser.getFloatTimeDomainData(this.levelData);
      let sum = 0;
      for (const v of this.levelData) sum += v * v;
      const rms = Math.sqrt(sum / this.levelData.length);
      if (this.onLevel) this.onLevel(Math.min(1, rms * LEVEL_SENSITIVITY));
      this.rafId = requestAnimationFrame(tick);
    };
    this.rafId = requestAnimationFrame(tick);
  }

  pause() {
    if (this.mediaRecorder && this.mediaRecorder.state === "recording") {
      this.mediaRecorder.pause();
      this.paused = true;
    }
  }

  resume() {
    if (this.mediaRecorder && this.mediaRecorder.state === "paused") {
      this.mediaRecorder.resume();
      this.paused = false;
    }
  }

  async stop() {
    return new Promise((resolve) => {
      if (!this.mediaRecorder) {
        resolve(null);
        return;
      }
      const mime = this.mediaRecorder.mimeType || "audio/webm";
      this.mediaRecorder.addEventListener("stop", () => {
        this._cleanup();
        resolve(this._takeBlob(mime));
      });
      this.mediaRecorder.stop();
    });
  }

  // Release the mic, recorder and meter without keeping the audio: the
  // recorder returns to fresh state. Safe to call when nothing is running.
  reset() {
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      this.mediaRecorder.stop();
    }
    this._cleanup();
    this.mediaRecorder = null;
    this.chunks = [];
    this.paused = false;
  }

  _takeBlob(mime) {
    // Build the Blob from the chunks, then release them from memory at once.
    if (this.chunks.length === 0) return null;
    const blob = new Blob(this.chunks, { type: mime });
    this.chunks = [];
    return blob;
  }

  _cleanup() {
    if (this.rafId) cancelAnimationFrame(this.rafId);
    this.rafId = null;
    if (this.audioContext) {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
    this.analyser = null;
  }
}

export function fileExtensionForMime(mime) {
  if (mime.includes("mp4")) return "mp4";
  if (mime.includes("ogg")) return "ogg";
  if (mime.includes("mpeg") || mime.includes("mp3")) return "mp3";
  if (mime.includes("wav")) return "wav";
  if (mime.includes("m4a")) return "m4a";
  return "webm";
}

export function blobToFile(blob, baseName) {
  const ext = fileExtensionForMime(blob.type);
  return new File([blob], `${baseName}.${ext}`, { type: blob.type });
}

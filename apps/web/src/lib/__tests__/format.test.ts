import { describe, expect, it } from "vitest";

import { formatClock, formatDuration, metaLine } from "../format";
import type { MeetingJob } from "../schemas";

function makeJob(overrides: Partial<MeetingJob> = {}): MeetingJob {
  return {
    id: "0123456789ab",
    created_at: "2026-08-22T10:00:00",
    status: "done",
    stages: [],
    duration_s: null,
    error_ar: null,
    sentences: [],
    speakers: [],
    analysis: null,
    date_gregorian: null,
    date_hijri: null,
    ...overrides,
  };
}

describe("formatClock", () => {
  it("formats seconds below one hour as MM:SS", () => {
    expect(formatClock(65)).toBe("01:05");
    expect(formatClock(0)).toBe("00:00");
    expect(formatClock(3599)).toBe("59:59");
  });

  it("rolls over into hours", () => {
    expect(formatClock(3600)).toBe("1:00:00");
    expect(formatClock(3661)).toBe("1:01:01");
  });
});

describe("formatDuration", () => {
  it("renders h:mm:ss at or above 3600 seconds", () => {
    expect(formatDuration(3600)).toBe("1:00:00");
    expect(formatDuration(3661)).toBe("1:01:01");
    expect(formatDuration(7325)).toBe("2:02:05");
  });

  it("renders MM:SS below one hour", () => {
    expect(formatDuration(65)).toBe("01:05");
    expect(formatDuration(599)).toBe("09:59");
  });

  it("clamps negative input to zero", () => {
    expect(formatDuration(-5)).toBe("00:00");
  });
});

describe("metaLine", () => {
  it("joins date, hijri, duration and speaker count with middle dots", () => {
    const job = makeJob({
      date_gregorian: "2026-08-22",
      date_hijri: "1448-02-28",
      duration_s: 3661,
      speakers: [
        { id: "s1", label: "أحمد", first_start: 0 },
        { id: "s2", label: "سارة", first_start: 12 },
      ],
    });
    expect(metaLine(job)).toBe("2026-08-22 · 1448-02-28 هـ · المدة: 1:01:01 · 2 متحدثان");
  });

  it("omits empty slots", () => {
    expect(metaLine(makeJob())).toBe("");
    expect(metaLine(makeJob({ duration_s: 65 }))).toBe("المدة: 01:05");
    expect(metaLine(makeJob({ date_gregorian: "2026-08-22" }))).toBe("2026-08-22");
  });
});

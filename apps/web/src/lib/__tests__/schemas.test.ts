import { describe, expect, it } from "vitest";

import { meetingJobSchema } from "../schemas";

const minimalJob = {
  id: "0123456789ab",
  created_at: "2026-08-22T10:00:00",
  status: "done",
  stages: [
    { key: "convert", label_ar: "تحويل", state: "done" },
    { key: "transcribe", label_ar: "تفريغ", state: "done" },
  ],
  duration_s: 125.5,
  error_ar: null,
  sentences: [
    { id: "s1", start: 0, end: 1.2, text: "أهلًا", speaker: "SPEAKER_00" },
  ],
  speakers: [{ id: "SPEAKER_00", label: "متحدث 1", first_start: 0 }],
  analysis: {
    title: "محضر الاجتماع",
    attendees: ["أحمد"],
    topics: [{ title: "افتتاح", summary: "تم الافتتاح", segment_ids: ["s1"] }],
    decisions: [],
    directives: [],
    tasks: [],
  },
  date_gregorian: "2026-08-22",
  date_hijri: "1448-02-28",
};

describe("meetingJobSchema", () => {
  it("parses a valid minimal job", () => {
    const job = meetingJobSchema.parse(minimalJob);
    expect(job.id).toBe("0123456789ab");
    expect(job.status).toBe("done");
    expect(job.analysis?.title).toBe("محضر الاجتماع");
    expect(job.sentences).toHaveLength(1);
  });

  it("applies defaults for optional array fields", () => {
    const job = meetingJobSchema.parse({
      id: "0123456789ab",
      created_at: "2026-08-22T10:00:00",
      status: "received",
    });
    expect(job.stages).toEqual([]);
    expect(job.sentences).toEqual([]);
    expect(job.speakers).toEqual([]);
  });

  it("rejects an empty object", () => {
    expect(() => meetingJobSchema.parse({})).toThrow();
  });

  it("rejects an invalid status", () => {
    expect(() => meetingJobSchema.parse({ ...minimalJob, status: "nope" })).toThrow();
  });
});

import { describe, expect, it } from "vitest";

import { SPEAKER_PALETTE, speakerColor } from "../config";

describe("speakerColor", () => {
  it("is stable for the same id", () => {
    expect(speakerColor("SPEAKER_00")).toBe(speakerColor("SPEAKER_00"));
  });

  it("returns a palette entry", () => {
    expect(SPEAKER_PALETTE).toContain(speakerColor("SPEAKER_00"));
    expect(SPEAKER_PALETTE).toContain(speakerColor("SPEAKER_07"));
  });

  it("produces different colors for adjacent ids", () => {
    const seen = new Set(["SPEAKER_00", "SPEAKER_01", "SPEAKER_02", "SPEAKER_03"].map((id) => speakerColor(id).bg));
    expect(seen.size).toBeGreaterThan(1);
  });
});

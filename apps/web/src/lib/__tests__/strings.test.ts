import { describe, expect, it } from "vitest";

import { sentencesCount, speakerCount } from "../strings";

describe("sentencesCount", () => {
  it("uses singular for 1", () => {
    expect(sentencesCount(1)).toBe("1 جملة");
  });
  it("uses dual for 2", () => {
    expect(sentencesCount(2)).toBe("2 جملتان");
  });
  it("uses plural for 3..10", () => {
    expect(sentencesCount(3)).toBe("3 جمل");
    expect(sentencesCount(10)).toBe("10 جمل");
  });
  it("falls back to singular form above 10", () => {
    expect(sentencesCount(11)).toBe("11 جملة");
    expect(sentencesCount(25)).toBe("25 جملة");
  });
});

describe("speakerCount", () => {
  it("uses singular for 1", () => {
    expect(speakerCount(1)).toBe("1 متحدث");
  });
  it("uses dual for 2", () => {
    expect(speakerCount(2)).toBe("2 متحدثان");
  });
  it("uses plural for 3 and above", () => {
    expect(speakerCount(3)).toBe("3 متحدثين");
    expect(speakerCount(10)).toBe("10 متحدثين");
  });
});

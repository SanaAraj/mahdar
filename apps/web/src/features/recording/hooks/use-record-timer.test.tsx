import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useRecordTimer } from "./use-record-timer";

describe("useRecordTimer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("preserves elapsed time across pause and resume", () => {
    const { result, rerender } = renderHook(
      ({ running, paused }) => useRecordTimer({ running, paused }),
      { initialProps: { running: true, paused: false } },
    );

    act(() => vi.advanceTimersByTime(2500));
    expect(result.current.elapsedSeconds).toBe(2);

    rerender({ running: true, paused: true });
    act(() => vi.advanceTimersByTime(3000));
    expect(result.current.elapsedSeconds).toBe(2);

    rerender({ running: true, paused: false });
    act(() => vi.advanceTimersByTime(2000));
    expect(result.current.elapsedSeconds).toBe(4);
  });

  it("starts a new recording from zero", () => {
    const { result, rerender } = renderHook(
      ({ running, paused }) => useRecordTimer({ running, paused }),
      { initialProps: { running: true, paused: false } },
    );

    act(() => vi.advanceTimersByTime(2000));
    rerender({ running: false, paused: false });
    rerender({ running: true, paused: false });
    expect(result.current.elapsedSeconds).toBe(0);
  });
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, uploadMeetingFile } from "@/lib/api-client";

import { useUpload } from "./use-upload";

const navigate = vi.fn();

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => navigate,
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, uploadMeetingFile: vi.fn() };
});

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;
}

describe("useUpload", () => {
  beforeEach(() => {
    navigate.mockReset();
    vi.mocked(uploadMeetingFile).mockReset();
  });

  it("clears progress and exposes the Arabic API error after failure", async () => {
    vi.mocked(uploadMeetingFile).mockImplementation((_file, _name, options) => {
      options?.onProgress?.(100);
      return Promise.reject(new ApiError(413, "upload.file_too_large", "الملف كبير"));
    });
    const { result } = renderHook(() => useUpload(), { wrapper });

    act(() => result.current.upload(new File(["audio"], "meeting.mp3")));

    await waitFor(() => expect(result.current.isPending).toBe(false));
    expect(result.current.progressPct).toBe(0);
    expect(result.current.error?.message_ar).toBe("الملف كبير");
    expect(navigate).not.toHaveBeenCalled();
  });
});

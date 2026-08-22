import { useMutation, useQueryClient } from "@tanstack/react-query";

import { reanalyze, type ApiError } from "@/lib/api-client";

interface UseReanalyzeResult {
  reanalyze: () => void;
  isPending: boolean;
  error: ApiError | null;
}

export function useReanalyze(meetingId: string): UseReanalyzeResult {
  const queryClient = useQueryClient();
  const mutation = useMutation<{ id: string }, ApiError, void>({
    mutationFn: () => reanalyze(meetingId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["meeting", meetingId] });
    },
  });

  return {
    reanalyze: () => mutation.mutate(),
    isPending: mutation.isPending,
    error: mutation.error ?? null,
  };
}

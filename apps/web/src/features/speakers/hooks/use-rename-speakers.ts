import { useMutation, useQueryClient } from "@tanstack/react-query";

import { renameSpeakers } from "@/lib/api-client";
import type { Speaker } from "@/lib/schemas";

export interface RenameInput {
  speakerId: string;
  label: string;
}

export function useRenameSpeakers(meetingId: string) {
  const queryClient = useQueryClient();
  return useMutation<Speaker[], unknown, RenameInput>({
    mutationFn: ({ speakerId, label }) =>
      renameSpeakers(meetingId, { [speakerId]: label }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["meeting", meetingId] });
    },
  });
}

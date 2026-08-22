import { useQuery } from "@tanstack/react-query";

import { getMeeting } from "@/lib/api-client";
import { POLL_INTERVAL_MS } from "@/lib/config";
import type { MeetingJob } from "@/lib/schemas";
import { isTerminal } from "../utils/meeting-status";

export function useMeetingJob(meetingId: string) {
  return useQuery<MeetingJob>({
    queryKey: ["meeting", meetingId],
    queryFn: () => getMeeting(meetingId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && isTerminal(status)) return false;
      return POLL_INTERVAL_MS;
    },
  });
}

import type { TaskPriority } from "@/lib/schemas";
import { strings } from "@/lib/strings";
import { Badge } from "@/components/ui/badge";

const LEVEL_BY_PRIORITY: Readonly<Record<TaskPriority, "danger" | "warn" | "success">> = {
  [strings.priorityHigh]: "danger",
  [strings.priorityMedium]: "warn",
  "منخفضة": "success",
};

interface PriorityBadgeProps {
  priority: TaskPriority;
}

export function PriorityBadge({ priority }: PriorityBadgeProps) {
  return <Badge variant={LEVEL_BY_PRIORITY[priority]}>{priority}</Badge>;
}

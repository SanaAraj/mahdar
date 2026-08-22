import type { DueDate } from "@/lib/schemas";
import { strings } from "@/lib/strings";

interface DueDateCellProps {
  due: DueDate;
}

export function DueDateCell({ due }: DueDateCellProps) {
  const gregorian = due.gregorian || due.raw || null;
  if (gregorian == null && due.hijri == null) return null;

  return (
    <span className="text-xs whitespace-nowrap text-[var(--color-ink-soft)] tabular-nums">
      {gregorian != null ? <bdi>{gregorian}</bdi> : null}
      {due.hijri != null && due.gregorian != null ? (
        <bdi>{` · ${due.hijri}${strings.hijriSuffix}`}</bdi>
      ) : null}
    </span>
  );
}

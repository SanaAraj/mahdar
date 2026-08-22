import type { TaskItem } from "@/lib/schemas";
import { strings } from "@/lib/strings";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PriorityBadge } from "./priority-badge";
import { DueDateCell } from "./due-date-cell";

interface TasksTableProps {
  tasks: TaskItem[];
  onSeek: (sentenceId: string) => unknown;
}

export function TasksTable({ tasks, onSeek }: TasksTableProps) {
  if (tasks.length === 0) {
    return <p className="m-0 text-sm text-[var(--color-ink-soft)]">{strings.tasksEmpty}</p>;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{strings.colTask}</TableHead>
          <TableHead>{strings.colOwner}</TableHead>
          <TableHead>{strings.colPriority}</TableHead>
          <TableHead>{strings.colDue}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {tasks.map((task, index) => {
          const firstSegment = task.segment_ids[0];
          const seekable = firstSegment != null;
          return (
            <TableRow
              key={`${task.description}-${index}`}
              tabIndex={seekable ? 0 : undefined}
              onClick={seekable ? () => onSeek(firstSegment) : undefined}
              onKeyDown={
                seekable
                  ? (event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        onSeek(firstSegment);
                      }
                    }
                  : undefined
              }
              className={seekable ? "cursor-pointer" : undefined}
            >
              <TableCell>{task.description}</TableCell>
              <TableCell className="text-[var(--color-ink-soft)]">{task.owner ?? strings.taskOwnerFallback}</TableCell>
              <TableCell>{task.priority ? <PriorityBadge priority={task.priority} /> : null}</TableCell>
              <TableCell>
                <DueDateCell due={task.due} />
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

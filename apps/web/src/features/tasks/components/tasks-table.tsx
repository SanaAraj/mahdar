import type { TaskItem } from "@/lib/schemas";
import { strings } from "@/lib/strings";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
    <>
      <div className="hidden sm:block">
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
                  <TableCell className="font-medium">{task.description}</TableCell>
                  <TableCell className="text-[var(--color-ink-soft)]">
                    {task.owner ?? strings.taskOwnerFallback}
                  </TableCell>
                  <TableCell>
                    {task.priority ? <PriorityBadge priority={task.priority} /> : null}
                  </TableCell>
                  <TableCell><DueDateCell due={task.due} /></TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
      <div className="space-y-3 sm:hidden">
        {tasks.map((task, index) => {
          const firstSegment = task.segment_ids[0];
          const seekable = firstSegment != null;
          return (
            <div
              key={`${task.description}-${index}`}
              role={seekable ? "button" : undefined}
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
              className="rounded-[16px] border border-[var(--color-line)] bg-[var(--color-bg)] p-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
            >
              <div className="mb-3 flex items-start justify-between gap-3">
                <strong className="text-sm leading-relaxed">{task.description}</strong>
                {task.priority ? <PriorityBadge priority={task.priority} /> : null}
              </div>
              <dl className="m-0 grid grid-cols-2 gap-3 text-xs">
                <div>
                  <dt className="text-[var(--color-ink-soft)]">{strings.colOwner}</dt>
                  <dd className="m-0 mt-1 font-semibold">{task.owner ?? strings.taskOwnerFallback}</dd>
                </div>
                <div>
                  <dt className="text-[var(--color-ink-soft)]">{strings.colDue}</dt>
                  <dd className="m-0 mt-1"><DueDateCell due={task.due} /></dd>
                </div>
              </dl>
            </div>
          );
        })}
      </div>
    </>
  );
}

import type { Decision, Directive, Topic } from "@/lib/schemas";
import { strings } from "@/lib/strings";
import { CitationChips } from "./citation-chips";
import { TopicCard } from "./topic-card";

interface MinutesSectionsProps {
  topics: Topic[];
  decisions: Decision[];
  directives: Directive[];
  startSeconds: Readonly<Record<string, number>>;
  onSeek: (sentenceId: string) => unknown;
}

export function MinutesSections({ topics, decisions, directives, startSeconds, onSeek }: MinutesSectionsProps) {
  return (
    <div className="flex flex-col gap-4">
      <section>
        <h4 className="m-0 mb-1.5 text-[15px] font-bold text-[var(--color-ink)]">{strings.topicsHeading}</h4>
        {topics.length === 0 ? (
          <p className="m-0 text-sm text-[var(--color-ink-soft)]">{strings.topicsEmpty}</p>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {topics.map((topic, index) => (
              <TopicCard
                key={`${topic.title}-${index}`}
                topic={topic}
                startSeconds={startSeconds}
                onSeek={onSeek}
              />
            ))}
          </ul>
        )}
      </section>
      <MinutesGroup heading={strings.decisionsHeading} emptyText={strings.decisionsEmpty} items={decisions} startSeconds={startSeconds} onSeek={onSeek} />
      <MinutesGroup heading={strings.directivesHeading} emptyText={strings.directivesEmpty} items={directives} startSeconds={startSeconds} onSeek={onSeek} />
    </div>
  );
}

interface MinutesGroupProps {
  heading: string;
  emptyText: string;
  items: ReadonlyArray<{ text: string; segment_ids: string[] }>;
  startSeconds: Readonly<Record<string, number>>;
  onSeek: (sentenceId: string) => unknown;
}

function MinutesGroup({ heading, emptyText, items, startSeconds, onSeek }: MinutesGroupProps) {
  return (
    <section>
      <h4 className="m-0 mb-1.5 text-[15px] font-bold text-[var(--color-ink)]">{heading}</h4>
      {items.length === 0 ? (
        <p className="m-0 text-sm text-[var(--color-ink-soft)]">{emptyText}</p>
      ) : (
        <ul className="m-0 mt-1 flex list-none flex-col gap-1.5 p-0">
          {items.map((item, index) => (
            <li key={index} className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
              <span>{item.text}</span>
              <CitationChips segmentIds={item.segment_ids} startSeconds={startSeconds} onSeek={onSeek} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

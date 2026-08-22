import * as React from "react";
import { Link } from "@tanstack/react-router";

import { cn } from "@/lib/utils";

interface AppHeaderProps {
  actions?: React.ReactNode;
  onNewMeeting?: () => void;
  className?: string;
}

export function AppHeader({ actions, onNewMeeting, className }: AppHeaderProps) {
  return (
    <header
      className={cn(
        "mb-6 border-b border-[var(--color-line)] px-0 py-3",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-5 max-[620px]:flex-col max-[620px]:items-stretch">
        {onNewMeeting ? (
          <button
            type="button"
            onClick={onNewMeeting}
            aria-label="اجتماع جديد: العودة إلى صفحة التسجيل"
            className="cursor-pointer rounded-[var(--radius)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)]"
          >
            <Brand />
          </button>
        ) : (
          <Link to="/" aria-label="اجتماع جديد: العودة إلى صفحة التسجيل">
            <Brand />
          </Link>
        )}
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
    </header>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-3 text-start">
      <svg
        viewBox="0 0 32 32"
        aria-hidden="true"
        className="h-10 w-10 shrink-0 rounded-[9px]"
      >
        <rect x="1.5" y="1.5" width="29" height="29" rx="7" fill="var(--color-accent)" />
        <rect
          x="1.5"
          y="1.5"
          width="29"
          height="29"
          rx="7"
          fill="none"
          stroke="var(--color-accent-dark)"
          strokeOpacity="0.35"
        />
        <rect x="10" y="10" width="12" height="2.2" rx="1.1" fill="#fff" />
        <rect x="10" y="15" width="12" height="2.2" rx="1.1" fill="#fff" />
        <rect x="10" y="20" width="8" height="2.2" rx="1.1" fill="#fff" />
      </svg>
      <div>
        <h1 className="m-0 text-[21px] font-bold leading-[1.3]">محضر</h1>
        <p className="m-0 text-xs text-[var(--color-ink-soft)] max-[460px]:hidden">
          تسجيل الاجتماعات وتفريغها الصوتي بالعربية
        </p>
      </div>
    </div>
  );
}

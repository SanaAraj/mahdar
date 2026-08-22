export function IconSprite() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
      <defs>
        <symbol id="icon-pause" viewBox="0 0 16 16" fill="currentColor">
          <path d="M4.5 3h2.6v10H4.5zM8.9 3h2.6v10H8.9z" />
        </symbol>
        <symbol id="icon-play" viewBox="0 0 16 16" fill="currentColor">
          <path d="M5 3.2v9.6L12.8 8z" />
        </symbol>
        <symbol id="icon-stop" viewBox="0 0 16 16" fill="currentColor">
          <rect x="4" y="4" width="8" height="8" rx="1.5" />
        </symbol>
        <symbol
          id="icon-upload"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M4 16.5V19a1.5 1.5 0 0 0 1.5 1.5h13A1.5 1.5 0 0 0 20 19v-2.5" />
          <path d="m7 9.5 5-5 5 5" />
          <path d="M12 4.5V15" />
        </symbol>
        <symbol
          id="icon-download"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M4 16.5V19a1.5 1.5 0 0 0 1.5 1.5h13A1.5 1.5 0 0 0 20 19v-2.5" />
          <path d="m7 14.5 5 5 5-5" />
          <path d="M12 19.5V9" />
        </symbol>
        <symbol
          id="icon-refresh"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 12a9 9 0 1 1-2.64-6.36" />
          <path d="M21 3v6h-6" />
        </symbol>
        <symbol
          id="icon-close"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M6 6l12 12M18 6L6 18" />
        </symbol>
        <symbol
          id="icon-chevron"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="m9 6 6 6-6 6" />
        </symbol>
        <symbol
          id="icon-check"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M4 12.5 9.5 18 20 6.5" />
        </symbol>
        <symbol
          id="icon-alert-circle"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7.5V13" />
          <path d="M12 16.5v.01" />
        </symbol>
        <symbol
          id="icon-mic"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="9" y="2.5" width="6" height="11" rx="3" />
          <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0" />
          <path d="M12 18v3.5" />
        </symbol>
      </defs>
    </svg>
  );
}

export type IconName =
  | "play"
  | "pause"
  | "stop"
  | "upload"
  | "download"
  | "refresh"
  | "close"
  | "chevron"
  | "check"
  | "alert-circle"
  | "mic";

export function iconHref(name: IconName): string {
  return `#icon-${name}`;
}

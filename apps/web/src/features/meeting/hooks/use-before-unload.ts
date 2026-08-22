import { useEffect } from "react";

export function useBeforeUnload(active: boolean): void {
  useEffect(() => {
    if (!active) return;
    function handler(event: BeforeUnloadEvent): void {
      event.preventDefault();
      event.returnValue = "";
    }
    window.addEventListener("beforeunload", handler);
    return () => {
      window.removeEventListener("beforeunload", handler);
    };
  }, [active]);
}

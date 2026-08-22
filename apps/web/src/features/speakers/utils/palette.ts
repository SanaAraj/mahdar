export { SPEAKER_PALETTE, type SpeakerColor } from "@/lib/config";

import { SPEAKER_PALETTE, type SpeakerColor } from "@/lib/config";

export function speakerColorFor(id: string): SpeakerColor {
  let hash = 0;
  for (const ch of id) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return SPEAKER_PALETTE[hash % SPEAKER_PALETTE.length];
}

export function speakerColorSlot(id: string): number {
  let hash = 0;
  for (const ch of id) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return hash % SPEAKER_PALETTE.length;
}

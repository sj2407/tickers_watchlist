import type { Snapshot } from "./types";

// Single source of truth for "what needs attention" ordering, shared by the board
// and the Tickers tab so the swipe/step order matches the list you see.
const leanRank: Record<string, number> = { exit: -1, trim: 0, pile_on: 1, hold: 2, watch: 3 };

export function attentionSorted(snap: Snapshot) {
  return [...snap.tickers].sort((a, b) => {
    const la = (a.final_lean ?? a.signals.provisional_lean) as string;
    const lb = (b.final_lean ?? b.signals.provisional_lean) as string;
    const ra = leanRank[la] ?? 9;
    const rb = leanRank[lb] ?? 9;
    if (ra !== rb) return ra - rb;
    return Math.abs(b.price?.day_change_pct ?? 0) - Math.abs(a.price?.day_change_pct ?? 0);
  });
}

/** Held names first (attention-sorted), then watch-only — used for the dropdown,
 * the prev/next arrows, and swipe stepping on the Tickers tab. */
export function tickerOrder(snap: Snapshot, heldSet: Set<string>) {
  const sorted = attentionSorted(snap).map((t) => t.ticker);
  const held = sorted.filter((s) => heldSet.has(s));
  const watch = sorted.filter((s) => !heldSet.has(s));
  return { order: [...held, ...watch], held, watch };
}

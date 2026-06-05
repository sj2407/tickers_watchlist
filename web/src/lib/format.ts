import type { Lean, Sentiment } from "./types";

export const usd = (n: number | null | undefined, dp = 2) =>
  n == null ? "—" : n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: dp, maximumFractionDigits: dp });

export const pct = (n: number | null | undefined, dp = 1) =>
  n == null ? "—" : `${n > 0 ? "+" : ""}${n.toFixed(dp)}%`;

export const num = (n: number | null | undefined, dp = 2) =>
  n == null ? "—" : n.toFixed(dp);

export const signClass = (n: number | null | undefined) =>
  n == null ? "text-zinc-400" : n > 0 ? "text-emerald-400" : n < 0 ? "text-rose-400" : "text-zinc-300";

export const leanLabel = (l: Lean | null): string =>
  l === "pile_on" ? "Pile on"
    : l === "trim" ? "Trim"
      : l === "exit" ? "Exit"
        : l === "watch" ? "Watch"
          : l === "hold" ? "Hold" : "—";

// Text-only color for the action word (no background pill).
export const leanTextClass = (l: Lean | null): string =>
  l === "pile_on" ? "text-emerald-300"
    : l === "trim" ? "text-amber-300"
      : l === "exit" ? "text-rose-300"
        : l === "watch" ? "text-sky-300"
          : "text-zinc-100"; // hold: neutral but bright

export const leanClass = (l: Lean | null): string =>
  l === "pile_on"
    ? "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30"
    : l === "trim"
      ? "bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/30"
      : l === "exit"
        ? "bg-rose-500/15 text-rose-300 ring-1 ring-rose-500/30"
        : l === "watch"
          ? "bg-sky-500/15 text-sky-300 ring-1 ring-sky-500/30"
          : "bg-zinc-500/15 text-zinc-300 ring-1 ring-zinc-500/30";

export const sentimentLabel = (s: Sentiment | null) =>
  s ? s.charAt(0).toUpperCase() + s.slice(1) : null;

export const sentimentClass = (s: Sentiment | null): string =>
  s === "bullish"
    ? "bg-emerald-500/15 text-emerald-300"
    : s === "bearish"
      ? "bg-rose-500/15 text-rose-300"
      : s === "mixed"
        ? "bg-amber-500/15 text-amber-300"
        : "bg-zinc-500/15 text-zinc-300";

// Plain-English reads of the raw numbers, so the page explains itself.
export const rsiWord = (rsi: number | null | undefined) =>
  rsi == null ? "" : rsi >= 70 ? "overbought" : rsi <= 35 ? "oversold" : "neutral";

export const trendWord = (t: string | null | undefined) =>
  t === "uptrend" ? "Uptrend" : t === "downtrend" ? "Downtrend" : t === "mixed" ? "Mixed" : "—";

export const relVolWord = (rv: number | null | undefined) =>
  rv == null ? "" : rv >= 2 ? "heavy" : rv >= 1.2 ? "above avg" : rv >= 0.8 ? "normal" : "light";

export const earningsWhen = (days: number | null | undefined) => {
  if (days == null) return "";
  if (days < 0) return "reported";
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  if (days <= 7) return `in ${days} days`;
  if (days <= 31) return `in ${Math.round(days / 7)} wk`;
  return `in ${Math.round(days / 30)} mo`;
};

export const toneClass = (tone: string): string =>
  ({
    good: "bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-500/20",
    bad: "bg-rose-500/10 text-rose-300 ring-1 ring-rose-500/20",
    warn: "bg-amber-500/10 text-amber-300 ring-1 ring-amber-500/20",
    info: "bg-sky-500/10 text-sky-300 ring-1 ring-sky-500/20",
  })[tone] ?? "bg-zinc-500/10 text-zinc-300 ring-1 ring-zinc-500/20";

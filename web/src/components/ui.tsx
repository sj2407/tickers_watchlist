import type { Badge as BadgeT, Lean, Sentiment } from "@/lib/types";
import { toneClass, leanClass, leanLabel, sentimentClass, sentimentLabel } from "@/lib/format";

export function SentimentChip({ sentiment }: { sentiment: Sentiment | null }) {
  if (!sentiment) return null;
  const dot = sentiment === "bullish" ? "▲" : sentiment === "bearish" ? "▼" : "●";
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${sentimentClass(sentiment)}`}>
      <span className="text-[9px]">{dot}</span>
      {sentimentLabel(sentiment)}
    </span>
  );
}

type Accent = "sky" | "emerald" | "violet" | "amber" | "rose" | "zinc";
const accentBar: Record<Accent, string> = {
  sky: "bg-sky-500/70",
  emerald: "bg-emerald-500/70",
  violet: "bg-violet-500/70",
  amber: "bg-amber-500/70",
  rose: "bg-rose-500/70",
  zinc: "bg-zinc-600",
};

export function SectionHeader({
  title,
  accent = "zinc",
  children,
}: {
  title: string;
  accent?: Accent;
  children?: React.ReactNode;
}) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <span className={`h-4 w-1 rounded-full ${accentBar[accent]}`} />
      <h2 className="text-sm font-semibold text-zinc-100">{title}</h2>
      {children}
    </div>
  );
}

// A labeled number with an optional plain-English read underneath.
export function Metric({
  label,
  value,
  hint,
  className = "",
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  className?: string;
}) {
  return (
    <div className="flex flex-col">
      <span className="text-[11px] font-medium uppercase tracking-wide text-zinc-300">{label}</span>
      <span className={`text-sm tabular-nums ${className}`}>{value}</span>
      {hint && <span className="text-[11px] text-zinc-400">{hint}</span>}
    </div>
  );
}

export function Badge({ badge }: { badge: BadgeT }) {
  return (
    <span className={`rounded-md px-2 py-0.5 text-xs font-medium ${toneClass(badge.tone)}`}>
      {badge.label}
    </span>
  );
}

export function BadgeRow({ badges }: { badges: BadgeT[] }) {
  if (!badges?.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {badges.map((b, i) => (
        <Badge key={i} badge={b} />
      ))}
    </div>
  );
}

export function LeanPill({ lean, provisional }: { lean: Lean | null; provisional?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${leanClass(lean)}`}>
      {leanLabel(lean)}
      {provisional && <span className="opacity-60">(auto)</span>}
    </span>
  );
}

export function Stat({ label, value, className = "" }: { label: string; value: React.ReactNode; className?: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[11px] uppercase tracking-wide text-zinc-500">{label}</span>
      <span className={`text-sm tabular-nums ${className}`}>{value}</span>
    </div>
  );
}

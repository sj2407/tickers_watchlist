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

export function SectionHeader({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-sm font-medium text-zinc-200">{title}</h2>
      {hint && <p className="text-xs text-zinc-500">{hint}</p>}
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
      <span className="text-[11px] uppercase tracking-wide text-zinc-500">{label}</span>
      <span className={`text-sm tabular-nums ${className}`}>{value}</span>
      {hint && <span className="text-[11px] text-zinc-500">{hint}</span>}
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

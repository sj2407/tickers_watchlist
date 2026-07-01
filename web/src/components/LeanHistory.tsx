import type { Lean } from "@/lib/types";
import type { LeanHistoryPoint } from "@/lib/data";
import { leanLabel } from "@/lib/format";
import { SectionHeader } from "@/components/ui";

// Same palette as the decision matrix so a color reads the same everywhere.
const DOT: Record<string, string> = {
  exit: "#e11d48", trim: "#fb7185", hold: "#93c5fd", pile_on: "#34d399", watch: "#a1a1aa",
};

function fmtWhen(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone: "America/New_York",
  });
}

// A compact strip of the call over time — one bar per run, oldest → newest. Answers the
// "is this the first time it went trim, and when did it actually flip?" question that the
// single-snapshot board can't. A change from the prior run is ringed; a call the quant did
// not propose (an override) gets a dashed inner outline. Hidden until there's a trajectory.
export default function LeanHistory({ points }: { points: LeanHistoryPoint[] }) {
  const chron = [...points].reverse().filter((p) => p.final_lean); // oldest → newest
  if (chron.length < 2) return null;

  // Most recent run whose call differs from the run before it.
  let lastChange: { from: Lean; to: Lean; at: string } | null = null;
  for (let i = chron.length - 1; i > 0; i--) {
    if (chron[i].final_lean !== chron[i - 1].final_lean) {
      lastChange = {
        from: chron[i - 1].final_lean as Lean,
        to: chron[i].final_lean as Lean,
        at: chron[i].generated_at,
      };
      break;
    }
  }
  const current = chron[chron.length - 1].final_lean as Lean;

  return (
    <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
      <SectionHeader title="Call history" accent="violet" />
      <div className="mt-1 flex flex-wrap items-end gap-1">
        {chron.map((p, i) => {
          const l = p.final_lean as Lean;
          const overridden = p.provisional_lean != null && p.provisional_lean !== l;
          const changed = i > 0 && chron[i - 1].final_lean !== l;
          return (
            <span
              key={p.generated_at}
              title={`${fmtWhen(p.generated_at)} · call: ${leanLabel(l)}${overridden ? ` (quant: ${leanLabel(p.provisional_lean as Lean)})` : ""}`}
              className={`inline-block h-5 w-2.5 rounded-sm ${changed ? "ring-2 ring-white/60" : ""}`}
              style={{
                background: DOT[l] ?? "#71717a",
                outline: overridden ? "1.5px dashed rgba(228,228,231,.7)" : undefined,
                outlineOffset: overridden ? "-4px" : undefined,
              }}
            />
          );
        })}
      </div>
      <p className="mt-2 text-[12px] leading-relaxed text-zinc-400">
        {lastChange ? (
          <>
            Last changed <span className="text-zinc-200">{leanLabel(lastChange.from)} → {leanLabel(lastChange.to)}</span> on {fmtWhen(lastChange.at)}.
          </>
        ) : (
          <>Held at <span className="text-zinc-200">{leanLabel(current)}</span> across the last {chron.length} runs.</>
        )}{" "}
        Bars are each run, oldest to newest; a ring marks a change from the run before it, a dashed outline a call the quant did not propose.
      </p>
    </section>
  );
}

import type { Ticker, Lean } from "@/lib/types";
import { SectionHeader } from "@/components/ui";
import { leanLabel } from "@/lib/format";

// Places each decision-driving metric on the same Exit | Trim | Hold | Pile-on axis,
// so you can see what each one points to and which ones drove the call. Faithful to the
// rule engine: dots are where each signal reads, the Decision dot is the rule's output.
const ZONE_BG =
  "linear-gradient(90deg, rgba(159,18,57,.18) 0 25%, rgba(251,113,133,.13) 25% 50%, rgba(147,197,253,.10) 50% 75%, rgba(52,211,153,.13) 75% 100%)";
const DOT = ["#e11d48", "#fb7185", "#93c5fd", "#34d399"]; // exit, trim, hold, pile
const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));

type Row = { name: string; value: string; zone: number; pos: number };

function growthZone(v: number): [number, number] {
  if (v >= 15) return [3, clamp(0.3 + (v - 15) / 100, 0.3, 0.95)];
  if (v >= 0) return [2, clamp(0.4 + (v / 15) * 0.5, 0.4, 0.92)];
  return [1, clamp(0.5 + v / 30, 0.05, 0.5)];
}

function buildRows(t: Ticker): Row[] {
  const tech = t.technicals ?? {};
  const f = t.fundamentals ?? null;
  const rs = t.relative_strength ?? {};
  const rows: Row[] = [];

  const tr = tech.trend;
  const cross = tech.ma_cross;
  if (tr || cross) {
    let zone = 2, pos = 0.5, value: string = tr ?? "mixed";
    if (cross === "death_cross" || tr === "downtrend") { zone = 1; pos = 0.4; value = cross === "death_cross" ? "death cross" : "downtrend"; }
    else if (tr === "uptrend" || cross === "golden_cross") { zone = 3; pos = 0.5; value = "uptrend"; }
    rows.push({ name: "Trend", value, zone, pos });
  }

  const r20 = rs.rs20d;
  if (r20 != null) {
    // Zone follows the engine: only an UNDERPERFORMING REGIME (RS line below its
    // 50-session MA) reads as deterioration; a small negative month inside a good
    // regime sits in the hold zone — never trim fuel.
    const under = rs.rs_trend === "underperforming";
    const zone = under ? 1 : r20 >= 0 ? 3 : 2;
    const pos = under
      ? clamp(0.6 + r20 / 20, 0.05, 0.6)
      : r20 >= 0
        ? clamp(0.3 + r20 / 20, 0.3, 0.95)
        : clamp(0.5 + r20 / 20, 0.15, 0.5);
    const label = `${r20 >= 0 ? "+" : ""}${r20.toFixed(1)}% vs SPY${under ? ", lagging regime" : ""}`;
    rows.push({ name: "Rel. strength", value: label, zone, pos });
  }

  // TTM honesty (P7): the matrix shows the value the ENGINE uses — single-quarter
  // YoY when our statements have it, else the source growth labelled for what it is.
  const isTtm = (f?.source ?? "").startsWith("equity-cache");
  const rev = f?.revenue_yoy_q ?? f?.revenue_yoy;
  if (rev != null) {
    const [zone, pos] = growthZone(rev);
    const name = f?.revenue_yoy_q != null ? "Revenue YoY" : isTtm ? "Revenue TTM" : "Revenue YoY";
    rows.push({ name, value: `${rev >= 0 ? "+" : ""}${rev.toFixed(0)}%`, zone, pos });
  }
  const eps = f?.eps_yoy_q ?? f?.eps_yoy;
  if (eps != null) {
    const [zone, pos] = growthZone(eps);
    const name = f?.eps_yoy_q != null ? "EPS YoY" : isTtm ? "EPS TTM" : "EPS growth";
    rows.push({ name, value: `${eps >= 0 ? "+" : ""}${eps.toFixed(0)}%`, zone, pos });
  }

  if (t.thesis_break?.margin_compression === true) {
    rows.push({ name: "Gross margin", value: "compressing", zone: 1, pos: 0.45 });
  } else if (f?.gross_margin != null) {
    rows.push({ name: "Gross margin", value: `${f.gross_margin.toFixed(0)}%`, zone: 2, pos: 0.5 });
  }

  if (tech.rsi14 != null) {
    const v = tech.rsi14;
    rows.push({ name: "RSI", value: `${v.toFixed(0)}${v >= 70 ? ", overbought" : v <= 30 ? ", oversold" : ""}`, zone: 2, pos: clamp((v - 30) / 40, 0.08, 0.95) });
  }
  if (tech.dist_sma20_pct != null) {
    const v = tech.dist_sma20_pct;
    rows.push({ name: "vs 20-day", value: `${v >= 0 ? "+" : ""}${v.toFixed(0)}%${v >= 12 ? ", extended" : ""}`, zone: 2, pos: clamp(0.5 + v / 24, 0.08, 0.95) });
  }
  return rows;
}

const DET_PHRASE: Record<string, string> = {
  downtrend: "downtrend",
  negative_rel_strength: "lagging the market",
  revenue_weakening: "revenue weakening",
  margin_compression: "margin compression",
  earnings_quality_deteriorating: "earnings quality slipping",
};

const leanZone = (l: Lean): number => (l === "exit" ? 0 : l === "trim" ? 1 : l === "pile_on" ? 3 : 2);

// The clean, rule-faithful explanation for a call the quant itself proposed and that
// didn't move since last run — the divergence framing in buildNote wraps around this.
function ruleNote(t: Ticker, lean: Lean): string {
  const d = t.signals?.drivers;
  const det = (d?.deterioration ?? []).map((k) => DET_PHRASE[k] ?? k);
  const blocks = d?.blocks ?? [];
  if (lean === "exit") return `Confirmed thesis break: ${det.join(", ") || "escalated by the read"}. Exit closes the position.`;
  if (lean === "trim") return `${det.length} deterioration signals (${det.join(", ")}); two or more, at least one of them hard (downtrend, revenue decline, severe margin collapse), triggers a trim.`;
  if (lean === "pile_on") return "Strong and leading the market with room to add, and no deterioration signals.";
  if (d?.review) return `Several soft signals (${det.join(", ")}) are worth a review, but a trim needs at least one hard signal (downtrend, revenue decline, or a severe margin collapse), so hold.`;
  if (blocks.length) return `Strong, but ${blocks.join(" and ")}, which removes the room to add (do not chase).`;
  if (det.length === 1) return `Only 1 deterioration signal (${det[0]}); a trim needs two, and it is not clear enough to add, so hold.`;
  return "Not strong enough to add and nothing deteriorating to trim, so hold.";
}

// Honest framing: when the call differs from the quant proposal (an override) or from
// the board's last call (a run-over-run flip), say so plainly and lead with the FRESH
// reason the routine named — never let a standing datapoint read as a new trigger.
function buildNote(t: Ticker, lean: Lean): string {
  const prov = t.signals?.provisional_lean ?? null;
  const prior = t.prior_lean ?? null;
  const reason = t.lean_change_reason?.trim() || null;
  const overridden = prov != null && prov !== lean;
  const changed = prior != null && prior !== lean;

  if (!overridden && !changed) return ruleNote(t, lean);

  const clauses: string[] = [];
  if (changed) clauses.push(`Changed from ${leanLabel(prior!)} to ${leanLabel(lean)} since the last run`);
  if (overridden)
    clauses.push(
      `${changed ? "the quant reads" : "Quant reads"} ${leanLabel(prov!)}, overridden by the qualitative read`,
    );
  let s = clauses.join("; ") + ".";
  // The routine is required to name what materially changed (ROUTINE.md). If it did,
  // lead with it; if it didn't, flag the gap rather than restating a stale signal.
  s += reason ? ` ${reason}` : " No fresh reason was recorded for this change — see the rationale above.";
  return s;
}

function Track({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative h-5 flex-1 rounded-md ring-1 ring-zinc-800" style={{ background: ZONE_BG }}>
      {[25, 50, 75].map((s) => (
        <span key={s} className="absolute bottom-0 top-0 w-px bg-white/5" style={{ left: `${s}%` }} />
      ))}
      {children}
    </div>
  );
}

export default function DecisionMatrix({ t }: { t: Ticker }) {
  const rows = buildRows(t);
  if (!rows.length) return null;
  const lean = (t.final_lean ?? t.signals.provisional_lean) as Lean;
  const dz = leanZone(lean);
  const note = buildNote(t, lean);
  const prov = t.signals?.provisional_lean ?? null;
  const showQuant = prov != null && prov !== lean; // quant disagreed → show its ghost marker

  return (
    <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
      <SectionHeader title="Why this call" accent="violet" />
      <div className="mb-1 flex items-center gap-2">
        <div className="w-24 flex-none sm:w-28" />
        <div className="grid flex-1 grid-cols-4 text-center font-mono text-[10px] uppercase tracking-wide">
          <span className="text-rose-300">Exit</span>
          <span className="text-rose-300">Trim</span>
          <span className="text-sky-300">Hold</span>
          <span className="text-emerald-300">Pile on</span>
        </div>
      </div>
      {rows.map((r, i) => (
        <div key={i} className="flex items-center gap-2 py-1">
          <div className="w-24 flex-none text-[11.5px] leading-tight text-zinc-300 sm:w-28">
            {r.name} <span className="text-[10px] text-zinc-500">{r.value}</span>
          </div>
          <Track>
            <span
              className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-zinc-950"
              style={{ left: `${r.zone * 25 + r.pos * 25}%`, background: DOT[r.zone] }}
            />
          </Track>
        </div>
      ))}
      <div className="mt-2 flex items-center gap-2 border-t border-zinc-800 pt-2">
        <div className="w-24 flex-none text-[13px] font-bold text-zinc-100 sm:w-28">Decision</div>
        <div className="relative h-6 flex-1 rounded-md ring-1 ring-zinc-800" style={{ background: ZONE_BG }}>
          {[25, 50, 75].map((s) => (
            <span key={s} className="absolute bottom-0 top-0 w-px bg-white/5" style={{ left: `${s}%` }} />
          ))}
          {showQuant && (
            <span
              title={`Quant proposal: ${leanLabel(prov!)}`}
              className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-dashed border-zinc-300/70 bg-transparent"
              style={{ left: `${leanZone(prov!) * 25 + 12.5}%` }}
            />
          )}
          <span
            className="absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-zinc-950 ring-2 ring-white/50"
            style={{ left: `${dz * 25 + 12.5}%`, background: DOT[dz] }}
          />
        </div>
      </div>
      {showQuant && (
        <p className="mt-1.5 flex items-center gap-3 text-[10px] text-zinc-500">
          <span className="flex items-center gap-1"><span className="inline-block h-2.5 w-2.5 rounded-full border-2 border-dashed border-zinc-300/70" /> quant proposal</span>
          <span className="flex items-center gap-1"><span className="inline-block h-2.5 w-2.5 rounded-full ring-2 ring-white/50" style={{ background: DOT[dz] }} /> final call</span>
        </p>
      )}
      <p className="mt-2 text-[12px] leading-relaxed text-zinc-400">{note}</p>
    </section>
  );
}

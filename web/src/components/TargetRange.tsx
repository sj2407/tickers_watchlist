import type { PriceTarget } from "@/lib/types";
import { usd } from "@/lib/format";

// A faithful horizontal "analyst target range" strip: the low→high bar, ticks for
// median and mean (consensus), and a marker for the current price. It is NOT a true
// boxplot — the per-analyst targets needed for real quartiles/outliers aren't on our
// data plan, so we draw only the numbers we actually have (no invented percentiles).
export default function TargetRange({
  target,
  current,
}: {
  target: PriceTarget;
  current: number | null;
}) {
  const { low, high } = target;
  const median = target.median;
  const mean = target.mean;
  const consensus = mean ?? median; // mean preferred as "consensus" when present
  const n = target.num_analysts;

  // Domain pads the low→high range and always includes the current price so its
  // marker stays on-canvas even when price sits outside the analyst range.
  const lo = current != null ? Math.min(low, current) : low;
  const hi = current != null ? Math.max(high, current) : high;
  const pad = (hi - lo || 1) * 0.08;
  const d0 = lo - pad;
  const d1 = hi + pad;
  const pos = (x: number) => Math.max(0, Math.min(100, ((x - d0) / (d1 - d0)) * 100));

  const upside = current && consensus ? (consensus / current - 1) * 100 : null;
  const upClass = upside == null ? "text-zinc-400" : upside >= 0 ? "text-emerald-300" : "text-rose-300";
  const skew =
    mean != null && median != null
      ? mean > median * 1.02
        ? "skews high"
        : mean < median * 0.98
          ? "skews low"
          : "balanced"
      : null;

  const lowPct = pos(low);
  const highPct = pos(high);
  const curPct = current != null ? pos(current) : null;

  return (
    <div className="rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
      <div className="mb-3 flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-zinc-100">Analyst price targets</h3>
        <div className="text-right text-xs">
          <span className="text-zinc-400">consensus </span>
          <span className="font-semibold text-zinc-100">{usd(consensus, 0)}</span>
          {upside != null && (
            <span className={`ml-1 font-semibold ${upClass}`}>
              {upside >= 0 ? "+" : ""}
              {upside.toFixed(0)}%
            </span>
          )}
        </div>
      </div>

      {/* plot: mean label above, bar in the middle, current marker below */}
      <div className="relative mx-1 h-14">
        {/* mean (consensus) tick + label above the bar */}
        {mean != null && (
          <div className="absolute top-0 -translate-x-1/2" style={{ left: `${pos(mean)}%` }}>
            <div className="text-center text-[9px] leading-none text-emerald-300">avg</div>
            <div className="mx-auto mt-0.5 h-3 w-px bg-emerald-400" />
          </div>
        )}

        {/* the range track + low→high bar, vertically centered */}
        <div className="absolute left-0 right-0 top-1/2 h-px -translate-y-1/2 bg-zinc-800" />
        <div
          className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-gradient-to-r from-sky-500/40 via-zinc-500/40 to-emerald-500/40"
          style={{ left: `${lowPct}%`, width: `${Math.max(0, highPct - lowPct)}%` }}
        />
        {/* low / high end caps */}
        <div className="absolute top-1/2 h-2.5 w-px -translate-y-1/2 bg-zinc-500" style={{ left: `${lowPct}%` }} />
        <div className="absolute top-1/2 h-2.5 w-px -translate-y-1/2 bg-zinc-500" style={{ left: `${highPct}%` }} />
        {/* median tick (subtle) */}
        {median != null && (
          <div
            className="absolute top-1/2 h-2.5 w-px -translate-y-1/2 bg-zinc-300"
            style={{ left: `${pos(median)}%` }}
            title={`median ${usd(median, 0)}`}
          />
        )}

        {/* current price marker + label below */}
        {curPct != null && (
          <div className="absolute bottom-0 -translate-x-1/2" style={{ left: `${curPct}%` }}>
            <div className="mx-auto h-3 w-px bg-amber-300" />
            <div className="mt-0.5 whitespace-nowrap text-center text-[9px] font-semibold leading-none text-amber-300">
              now {usd(current, 0)}
            </div>
          </div>
        )}
      </div>

      {/* end labels + footnote */}
      <div className="mt-1 flex justify-between text-[10px] text-zinc-500">
        <span>low {usd(low, 0)}</span>
        <span>high {usd(high, 0)}</span>
      </div>
      <p className="mt-2 border-t border-zinc-800 pt-2 text-[10px] text-zinc-500">
        {n ? `${n} analyst${n === 1 ? "" : "s"}` : "analyst targets"}
        {median != null && <> · median {usd(median, 0)}</>}
        {skew && <> · range {skew}</>}
      </p>
    </div>
  );
}

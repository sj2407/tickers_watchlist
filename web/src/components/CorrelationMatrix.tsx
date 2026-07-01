"use client";
import { useMemo, useState } from "react";

// Co-movement & co-crash heatmap.
//  - Co-move  = Kendall's tau (robust rank correlation)
//  - Co-crash = Clayton lower tail dependence lambda_L, derived from tau:
//               theta = 2*tau/(1-tau),  lambda_L = 2^(-1/theta)
// Both use only the names' own daily returns (no benchmark, no tags). See the
// "How it's calculated" panel below the grid, and /methodology for the wider dictionary.

type Named = { ticker: string; closes: number[] };
type Mode = "tau" | "lambda";

const WINDOWS = [
  { k: 21, label: "1M" },
  { k: 63, label: "3M" },
  { k: 126, label: "6M" },
  { k: 9999, label: "Full" },
];
const WINLAB: Record<number, string> = { 21: "1 month", 63: "3 months", 126: "6 months", 9999: "full history" };

function returns(c: number[]): number[] {
  const r: number[] = [];
  for (let i = 1; i < c.length; i++) {
    const p = c[i - 1];
    r.push(p ? c[i] / p - 1 : 0);
  }
  return r;
}

// Kendall's tau-b
function kendall(a: number[], b: number[]): number {
  const n = a.length;
  let C = 0, D = 0, Tx = 0, Ty = 0;
  for (let i = 0; i < n; i++)
    for (let j = i + 1; j < n; j++) {
      const dx = a[i] - a[j], dy = b[i] - b[j], s = dx * dy;
      if (s > 0) C++;
      else if (s < 0) D++;
      else if (dx === 0 && dy === 0) { /* tied on both — skip */ }
      else if (dx === 0) Tx++;
      else Ty++;
    }
  const den = Math.sqrt((C + D + Tx) * (C + D + Ty));
  return den ? (C - D) / den : 0;
}
const clayTheta = (tau: number) => (2 * tau) / (1 - tau);
function lambdaL(tau: number): number {
  if (tau <= 0) return 0;
  if (tau >= 1) return 1;
  return Math.pow(2, -1 / clayTheta(tau));
}

// greedy nearest-neighbour seriation so co-moving names sit together
function clusterOrder(M: number[][]): number[] {
  const N = M.length;
  const used = new Array(N).fill(false);
  let start = 0, best = -2;
  for (let i = 0; i < N; i++) {
    let s = 0;
    for (let j = 0; j < N; j++) if (j !== i) s += M[i][j];
    if (s / (N - 1) > best) { best = s / (N - 1); start = i; }
  }
  const order = [start];
  used[start] = true;
  while (order.length < N) {
    const last = order[order.length - 1];
    let nx = -1, bc = -2;
    for (let j = 0; j < N; j++) if (!used[j] && M[last][j] > bc) { bc = M[last][j]; nx = j; }
    if (nx < 0) for (let j = 0; j < N; j++) if (!used[j]) { nx = j; break; }
    order.push(nx);
    used[nx] = true;
  }
  return order;
}

const STOPS: [number, number, number, number][] = [
  [-1, 33, 102, 172], [-0.5, 103, 169, 207], [0, 247, 247, 247], [0.5, 239, 138, 98], [1, 178, 24, 43],
];
function color(r: number): string {
  if (Number.isNaN(r)) return "#1a2030";
  r = Math.max(-1, Math.min(1, r));
  for (let i = 0; i < STOPS.length - 1; i++) {
    const [a, ar, ag, ab] = STOPS[i];
    const [b, br, bg, bb] = STOPS[i + 1];
    if (r >= a && r <= b) {
      const f = (r - a) / (b - a);
      return `rgb(${Math.round(ar + (br - ar) * f)},${Math.round(ag + (bg - ag) * f)},${Math.round(ab + (bb - ab) * f)})`;
    }
  }
  return "#f7f7f7";
}

function Seg<T extends string | number>({
  options, value, onChange,
}: { options: { v: T; label: React.ReactNode }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="inline-flex gap-0.5 rounded-xl border border-zinc-800 bg-zinc-900/70 p-0.5">
      {options.map((o) => {
        const on = o.v === value;
        return (
          <button
            key={String(o.v)}
            onClick={() => onChange(o.v)}
            className={`rounded-lg px-2.5 py-1.5 text-xs font-semibold transition ${
              on ? "bg-sky-500 text-sky-950" : "text-zinc-400 hover:text-zinc-100"
            }`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

export default function CorrelationMatrix({ names, asOf }: { names: Named[]; asOf: string }) {
  const [win, setWin] = useState(63);
  const [mode, setMode] = useState<Mode>("tau");
  const [hl, setHl] = useState(0.7);

  const RET = useMemo(() => names.map((n) => ({ t: n.ticker, r: returns(n.closes) })), [names]);
  const N = RET.length;
  const FULL = N ? Math.min(...RET.map((o) => o.r.length)) : 0;

  // Kendall tau matrix + cluster order, memoised per window (the expensive step)
  const { TAU, order, n } = useMemo(() => {
    const k = Math.min(win, FULL);
    const R = RET.map((o) => o.r.slice(o.r.length - k));
    const T: number[][] = Array.from({ length: N }, () => new Array(N).fill(1));
    for (let i = 0; i < N; i++)
      for (let j = i + 1; j < N; j++) {
        const t = kendall(R[i], R[j]);
        T[i][j] = T[j][i] = t;
      }
    return { TAU: T, order: clusterOrder(T), n: k };
  }, [RET, win, FULL, N]);

  const lam = mode === "lambda";
  const M = useMemo(
    () => (lam ? TAU.map((row, i) => row.map((t, j) => (i === j ? 1 : lambdaL(t)))) : TAU),
    [TAU, lam],
  );

  // narrative
  const { avg, topI, topJ, topV, divI, divV } = useMemo(() => {
    let pi = 0, pj = 1, pmax = -2, sum = 0, np = 0;
    for (let i = 0; i < N; i++)
      for (let j = i + 1; j < N; j++) {
        const c = M[i][j];
        sum += c; np++;
        if (c > pmax) { pmax = c; pi = i; pj = j; }
      }
    let di = 0, dlow = 2;
    for (let i = 0; i < N; i++) {
      let s = 0, c = 0;
      for (let j = 0; j < N; j++) if (j !== i) { s += M[i][j]; c++; }
      const a = c ? s / c : 0;
      if (a < dlow) { dlow = a; di = i; }
    }
    return { avg: np ? sum / np : 0, topI: pi, topJ: pj, topV: pmax, divI: di, divV: dlow };
  }, [M, N]);

  const pct = (x: number) => Math.round(x * 100);
  const tie = avg > 0.45 ? "tightly" : avg > 0.25 ? "moderately" : avg > 0.1 ? "loosely" : "barely";
  const ex = { tau: TAU[topI]?.[topJ] ?? 0 };
  const exTheta = clayTheta(ex.tau);
  const exLam = lambdaL(ex.tau);

  return (
    <div>
      {/* plain-English read */}
      <div className="rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
        {lam ? (
          <>
            <p className="text-sm font-semibold text-zinc-100">
              When one name craters, the rest follow about {pct(avg)}% of the time — average lower tail dependence λ<sub>L</sub> = {avg.toFixed(2)}.
            </p>
            <p className="mt-1 text-xs text-zinc-400">
              Crash together most: <span className="font-semibold text-zinc-200">{RET[topI]?.t} &amp; {RET[topJ]?.t} ({pct(topV)}%)</span>{" · "}
              Most independent in a selloff: <span className="font-semibold text-zinc-200">{RET[divI]?.t} (avg {pct(divV)}%)</span>{" · "}
              <span className="font-semibold text-zinc-200">{n}</span> trading days
            </p>
          </>
        ) : (
          <>
            <p className="text-sm font-semibold text-zinc-100">
              Over the last {WINLAB[win]}, the book moves {tie} together — average Kendall&apos;s τ = {avg.toFixed(2)}.
            </p>
            <p className="mt-1 text-xs text-zinc-400">
              Most joined at the hip: <span className="font-semibold text-zinc-200">{RET[topI]?.t} &amp; {RET[topJ]?.t} (τ {topV.toFixed(2)})</span>{" · "}
              Best diversifier: <span className="font-semibold text-zinc-200">{RET[divI]?.t} (avg τ {divV.toFixed(2)})</span>{" · "}
              <span className="font-semibold text-zinc-200">{n}</span> trading days
            </p>
          </>
        )}
      </div>

      {/* controls */}
      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-3">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">Window</span>
          <Seg options={WINDOWS.map((w) => ({ v: w.k, label: w.label }))} value={win} onChange={setWin} />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">Measure</span>
          <Seg<Mode>
            options={[{ v: "tau", label: "Co-move (τ)" }, { v: "lambda", label: <>Co-crash (λ<sub>L</sub>)</> }]}
            value={mode}
            onChange={setMode}
          />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">
            Highlight ≥ <span className="font-bold text-sky-300">{hl > 0 ? `${pct(hl)}%` : "off"}</span>
          </span>
          <input
            type="range" min={0} max={95} step={5} value={pct(hl)}
            onChange={(e) => setHl(Number(e.target.value) / 100)}
            className="h-1 w-32 cursor-pointer appearance-none rounded bg-zinc-700 accent-sky-400"
          />
        </div>
      </div>

      {/* heatmap */}
      <div className="mt-4 overflow-auto rounded-2xl bg-zinc-900/70 ring-1 ring-zinc-800">
        <table className="border-separate" style={{ borderSpacing: 0, fontVariantNumeric: "tabular-nums" }}>
          <thead>
            <tr>
              <th className="sticky left-0 top-0 z-30 bg-zinc-900" />
              {order.map((j) => (
                <th key={j} className="sticky top-0 z-20 h-16 bg-zinc-900 align-bottom pb-1.5 text-[10px] font-semibold text-zinc-400">
                  <div style={{ writingMode: "vertical-rl", transform: "rotate(180deg)", margin: "0 auto", whiteSpace: "nowrap" }}>
                    {RET[j].t}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {order.map((i, ri) => (
              <tr key={i}>
                <th className="sticky left-0 z-10 whitespace-nowrap bg-zinc-900 px-2 text-right text-[10.5px] font-semibold text-zinc-400">
                  {RET[i].t}
                </th>
                {order.map((j, cj) => {
                  if (cj >= ri) return <td key={j} className="h-[30px] w-[30px] bg-zinc-900" />;
                  const c = M[i][j];
                  const on = hl > 0;
                  const hot = on && c >= hl;
                  const dim = on && c < hl;
                  const tau = TAU[i][j];
                  return (
                    <td
                      key={j}
                      title={`${RET[i].t} ↔ ${RET[j].t}   τ=${tau.toFixed(2)}   co-crash λL=${pct(lambdaL(tau))}%   (${WINLAB[win]}, ${n}d)`}
                      className={`h-[30px] w-[30px] text-center text-[10px] tabular-nums ${
                        hot ? "font-extrabold" : "font-medium"
                      } ${dim ? "opacity-[0.16]" : ""}`}
                      style={{
                        color: "#0a0d14",
                        background: color(c),
                        boxShadow: hot ? "inset 0 0 0 2px rgba(255,255,255,.9)" : undefined,
                        borderRadius: hot ? 3 : undefined,
                      }}
                    >
                      {pct(c)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* legend */}
      <div className="mt-3 flex items-center gap-2.5 px-0.5 text-[11.5px] text-zinc-400">
        <span>{lam ? "0% (independent)" : "−100% (opposite)"}</span>
        <div>
          <div
            className="h-2.5 w-[200px] rounded"
            style={{
              background: lam
                ? "linear-gradient(90deg,#f7f7f7,#ef8a62,#b2182b)"
                : "linear-gradient(90deg,#2166ac,#67a9cf,#f7f7f7,#ef8a62,#b2182b)",
            }}
          />
          <div className="-mt-0.5 flex w-[200px] justify-between text-[10px]">
            {lam ? (<><span>0</span><span>50</span><span>100</span></>) : (<><span>−100</span><span>0</span><span>+100</span></>)}
          </div>
        </div>
        <span>{lam ? "100% (always together)" : "+100% (together)"}</span>
      </div>

      {/* how it's calculated */}
      <section className="mt-6 rounded-2xl bg-zinc-900/70 p-5 ring-1 ring-zinc-800">
        <h2 className="text-sm font-semibold text-zinc-100">How it&apos;s calculated</h2>
        <p className="mt-1 text-xs text-zinc-400">
          Co-crash is built in three steps — a robust correlation, mapped to a copula that allows joint crashes, read
          out as a probability. Every step uses only the names&apos; own daily returns (no benchmark, no manual tags).
        </p>

        {[
          {
            name: "Robust co-movement — Kendall's τ",
            formula: <>τ = (<i className="text-sky-300">C</i> − <i className="text-sky-300">D</i>) / √((C+D+Tₓ)(C+D+T_y))</>,
            cap: (
              <>
                <i>C</i> and <i>D</i> count <b className="text-zinc-200">concordant</b> vs <b className="text-zinc-200">discordant</b> day-pairs.{" "}
                <b className="text-zinc-200">Captures:</b> whether the two names tend to move the same direction, by <b className="text-zinc-200">rank</b> — outlier-proof and assumption-free (a single +40% earnings day can&apos;t swing it the way it swings Pearson).
              </>
            ),
          },
          {
            name: "Map to a copula that admits crashes — Clayton θ",
            formula: <>θ = 2τ / (1 − τ)</>,
            cap: (
              <>
                <b className="text-zinc-200">Captures:</b> the <b className="text-zinc-200">strength</b> of dependence in a copula whose shape <i>allows</i> joint extreme losses. Clayton has genuine lower-tail dependence — unlike a Gaussian copula, whose tail dependence is exactly zero (the 2008 mistake). θ comes straight from τ; no fitting, no truncated samples.
              </>
            ),
          },
          {
            name: "Co-crash probability — lower tail dependence λ_L",
            formula: <>λ<sub>L</sub> = 2<sup>(−1/θ)</sup></>,
            cap: (
              <>
                <b className="text-zinc-200">Captures exactly the question:</b> the limiting probability that one name is in its crash tail <b className="text-zinc-200">given the other already is</b>. λ<sub>L</sub> = 0 → crashes are independent; λ<sub>L</sub> → 1 → when one craters, the other almost always craters with it.
              </>
            ),
          },
        ].map((s, idx) => (
          <div key={idx} className="mt-3 grid grid-cols-[26px_1fr] gap-3 border-t border-zinc-800 pt-3">
            <div className="grid h-6 w-6 place-items-center rounded-full border border-zinc-800 bg-zinc-950 text-xs font-bold text-sky-300">
              {idx + 1}
            </div>
            <div>
              <div className="text-[12.5px] font-semibold text-zinc-100">{s.name}</div>
              <div className="my-2 inline-block rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-1.5 font-mono text-[13px] text-zinc-300">
                {s.formula}
              </div>
              <p className="text-xs leading-relaxed text-zinc-400">{s.cap}</p>
            </div>
          </div>
        ))}

        <div className="mt-3 border-t border-zinc-800 pt-3 text-xs leading-relaxed text-zinc-400">
          <b className="text-zinc-200">Worked example — {RET[topI]?.t} &amp; {RET[topJ]?.t} ({WINLAB[win]}):</b>{" "}
          τ = <code className="rounded border border-zinc-800 bg-zinc-950 px-1.5 text-sky-300">{ex.tau.toFixed(2)}</code> → θ ={" "}
          <code className="rounded border border-zinc-800 bg-zinc-950 px-1.5 text-sky-300">{exTheta.toFixed(1)}</code> → λ<sub>L</sub> ={" "}
          <code className="rounded border border-zinc-800 bg-zinc-950 px-1.5 text-sky-300">{pct(exLam)}%</code> co-crash probability.
        </div>
        <p className="mt-2.5 text-[11.5px] leading-relaxed text-zinc-500">
          Clayton models the <i>lower</i> tail only (λ<sub>U</sub> = 0 — names can crash together yet not melt up together, the
          right prior for equities); λ<sub>L</sub> is a parametric estimate and an asymptotic deep-tail limit, so read it as a
          calibrated ranking rather than a literal frequency. As of {asOf}. See <a className="text-sky-400 hover:underline" href="/methodology">Methodology</a> for the wider dictionary.
        </p>
      </section>
    </div>
  );
}

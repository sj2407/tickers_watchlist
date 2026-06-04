import Link from "next/link";
import metricsData from "@/lib/metrics.json";

interface MetricEntry {
  key: string;
  label: string;
  category: string;
  definition: string;
  how_computed: string;
  good_when: string;
  source_type: string;
}

const CATEGORY_ORDER = ["technical", "momentum", "fundamental", "thesis", "risk", "position", "event", "analyst"];
const CATEGORY_LABEL: Record<string, string> = {
  technical: "Technical", momentum: "Momentum & relative strength", fundamental: "Fundamentals",
  thesis: "Thesis-break flags", risk: "Risk / trade plan", position: "Your position",
  event: "Events", analyst: "Analyst",
};

export const metadata = { title: "Methodology — Watchlist" };

export default function Methodology() {
  const metrics = metricsData as MetricEntry[];
  const byCat = (c: string) => metrics.filter((m) => m.category === c);

  return (
    <main className="min-h-dvh bg-zinc-950 pb-20 text-zinc-100">
      <div className="mx-auto max-w-2xl px-4 pt-6">
        <Link href="/" className="text-sm text-sky-400">← Watchlist</Link>
        <h1 className="mt-3 text-xl font-semibold">Methodology &amp; dictionary</h1>
        <p className="mt-1 text-sm text-zinc-400">How the calls are made, and what every number means.</p>

        {/* How recommendations are made */}
        <section className="mt-5 rounded-2xl bg-zinc-900/70 p-5 ring-1 ring-zinc-800">
          <h2 className="text-sm font-medium text-zinc-200">How the call is made</h2>
          <p className="mt-2 text-sm leading-relaxed text-zinc-300">
            Each name gets a suggested action — <b>Pile on</b>, <b>Hold</b>, <b>Trim</b>, or <b>Exit</b>
            (or <b>Watch</b> if you don&apos;t hold it). It&apos;s built in two steps: a transparent
            rule layer proposes a lean from the signals below, then a reasoning pass weighs the news,
            earnings, and severity to make the final call.
          </p>
          <ul className="mt-3 space-y-1.5 text-sm text-zinc-300">
            <li><span className="text-emerald-300 font-medium">Pile on</span> — uptrend, leading the market, fundamentals intact, <i>and</i> room to add (not overbought/extended, not right before earnings). Entry guidance tells you where/when.</li>
            <li><span className="text-zinc-300 font-medium">Hold</span> — the default. Includes &quot;strong but overbought&quot; → don&apos;t chase, wait for a pullback.</li>
            <li><span className="text-amber-300 font-medium">Trim</span> — a <i>confluence</i> of deterioration (≥2 of: downtrend, weakening fundamentals, sustained underperformance vs the market, repeated earnings misses). Keeps at least the $200 floor.</li>
            <li><span className="text-rose-300 font-medium">Exit</span> — a <i>clear</i> thesis break (e.g. revenue rolling over + margins compressing, or guidance cut / catalyst failed). Closes the position.</li>
          </ul>
          <div className="mt-4 space-y-2 border-t border-zinc-800 pt-3 text-xs text-zinc-400">
            <p><b className="text-zinc-300">Trim/exit are driven by the thesis going wrong — never by position size.</b> This is a small thematic sleeve; a name being a large % of it is not a reason to sell.</p>
            <p>A single mild negative is not enough to trim — it takes a confluence. Overbought alone means &quot;don&apos;t chase,&quot; not &quot;sell.&quot;</p>
            <p>A breached stop is a <b>prompt to re-check the thesis</b>, not an automatic cut.</p>
            <p>Financial facts come only from live data or web search — never from model memory. This is <b>decision-support, not advice</b>; you place every order.</p>
          </div>
        </section>

        {/* Dictionary */}
        <h2 className="mb-2 mt-6 text-sm font-medium text-zinc-300">Dictionary</h2>
        {CATEGORY_ORDER.filter((c) => byCat(c).length > 0).map((cat) => (
          <section key={cat} className="mb-4">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">{CATEGORY_LABEL[cat] ?? cat}</h3>
            <div className="space-y-2">
              {byCat(cat).map((m) => (
                <div key={m.key} id={m.key} className="scroll-mt-4 rounded-xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-sm font-medium text-zinc-100">{m.label}</span>
                    <span className="text-[10px] uppercase tracking-wide text-zinc-600">{m.source_type.replace("_", " ")}</span>
                  </div>
                  <p className="mt-1 text-sm text-zinc-300">{m.definition}</p>
                  <p className="mt-1 text-xs text-zinc-500"><span className="text-zinc-400">How:</span> {m.how_computed}</p>
                  <p className="mt-0.5 text-xs text-zinc-500"><span className="text-zinc-400">Good when:</span> {m.good_when}</p>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}

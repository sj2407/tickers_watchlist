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
// Color metric names by group, matching the section accents used across the app.
// (Literal class strings so Tailwind's scanner includes them.)
const CATEGORY_ACCENT: Record<string, string> = {
  technical: "text-sky-300", momentum: "text-sky-300", fundamental: "text-emerald-300",
  thesis: "text-rose-300", risk: "text-amber-300", position: "text-emerald-300",
  event: "text-amber-300", analyst: "text-amber-300",
};
const CATEGORY_BAR: Record<string, string> = {
  technical: "bg-sky-400", momentum: "bg-sky-400", fundamental: "bg-emerald-400",
  thesis: "bg-rose-400", risk: "bg-amber-400", position: "bg-emerald-400",
  event: "bg-amber-400", analyst: "bg-amber-400",
};

export const metadata = { title: "Methodology · Watchlist" };

export default function Methodology() {
  const metrics = metricsData as MetricEntry[];
  const byCat = (c: string) => metrics.filter((m) => m.category === c);

  return (
    <main className="min-h-dvh bg-zinc-950 pb-20 text-zinc-100">
      <div className="mx-auto max-w-2xl px-4 pt-6">
        <h1 className="text-xl font-semibold">Methodology &amp; dictionary</h1>
        <p className="mt-1 text-sm text-zinc-400">How the calls are made, and what every number means.</p>

        {/* How recommendations are made */}
        <section className="mt-5 rounded-2xl bg-zinc-900/70 p-5 ring-1 ring-zinc-800">
          <h2 className="text-sm font-semibold text-zinc-100">How the call is made</h2>
          <p className="mt-2 text-sm leading-relaxed text-zinc-300">
            Each name gets a suggested action: <b>Pile on</b>, <b>Hold</b>, <b>Trim</b>, or <b>Exit</b>
            (or <b>Watch</b> if you don&apos;t hold it). It&apos;s built in two steps: a transparent
            rule layer proposes <b>Pile on / Hold / Trim</b> from the signals below; then a reasoning
            pass weighs the news, earnings, guidance and <i>severity</i> to confirm it, and it&apos;s
            the only step that escalates to <b>Exit</b>. The rules never call an Exit on their own.
          </p>
          <ul className="mt-3 space-y-1.5 text-sm text-zinc-300">
            <li><span className="text-emerald-300 font-medium">Pile on</span>: uptrend, <i>leading the market</i> (positive relative strength), fundamentals intact, <i>and</i> room to add (not overbought/extended, not within a day of earnings). Entry guidance tells you where/when.</li>
            <li><span className="text-zinc-300 font-medium">Hold</span>: the default. Includes &quot;strong but overbought&quot; → don&apos;t chase; a name reporting within a day → wait out the print; and a <i>single</i> mild negative (it takes a confluence to trim).</li>
            <li><span className="text-amber-300 font-medium">Trim</span>: a <i>confluence</i> of ≥2 distinct deterioration signals: confirmed downtrend, revenue weakening, gross-margin compression, sustained underperformance vs the market, or deteriorating earnings quality (negative EPS growth / repeated misses). Keeps at least the $200 floor.</li>
            <li><span className="text-rose-300 font-medium">Exit</span>: escalated by the reasoning pass on a <i>confirmed</i> thesis break (guidance cut, catalyst failed, or a clear multi-quarter breakdown, not one soft quarter). Closes the position fully (the only action that overrides the $200 floor).</li>
          </ul>
          <div className="mt-4 space-y-2 border-t border-zinc-800 pt-3 text-xs text-zinc-400">
            <p><b className="text-zinc-300">Trim/exit are driven by the thesis going wrong, never by position size.</b> This is a small thematic sleeve; a name being a large % of it is not a reason to sell.</p>
            <p>A single mild negative is not enough to trim; it takes a confluence. Overbought alone means &quot;don&apos;t chase,&quot; not &quot;sell.&quot;</p>
            <p>Fundamentals are quarterly and point-in-time; a small sequential margin dip is ignored for fast-growing names (normal noise, not a broken thesis). The $200 floor applies to trims; only an Exit closes a position fully.</p>
            <p>A breached stop is a <b>prompt to re-check the thesis</b>, not an automatic cut.</p>
            <p>Financial facts come only from live data or web search, never from model memory. This is <b>decision-support, not advice</b>; you place every order.</p>
          </div>
        </section>

        {/* Dictionary */}
        <h2 className="mb-2 mt-6 text-sm font-semibold text-zinc-100">Dictionary</h2>
        {CATEGORY_ORDER.filter((c) => byCat(c).length > 0).map((cat) => (
          <section key={cat} className="mb-4">
            <h3 className={`mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide ${CATEGORY_ACCENT[cat] ?? "text-zinc-300"}`}>
              <span className={`h-3 w-1 rounded-full ${CATEGORY_BAR[cat] ?? "bg-zinc-600"}`} />
              {CATEGORY_LABEL[cat] ?? cat}
            </h3>
            <div className="space-y-2">
              {byCat(cat).map((m) => (
                <div key={m.key} id={m.key} className="scroll-mt-4 rounded-xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className={`text-sm font-semibold ${CATEGORY_ACCENT[cat] ?? "text-zinc-100"}`}>{m.label}</span>
                    <span className="text-[10px] uppercase tracking-wide text-zinc-400">{m.source_type.replace("_", " ")}</span>
                  </div>
                  <p className="mt-1 text-sm text-zinc-300">{m.definition}</p>
                  <p className="mt-1 text-xs text-zinc-400"><span className="text-zinc-300">How:</span> {m.how_computed}</p>
                  <p className="mt-0.5 text-xs text-zinc-400"><span className="text-zinc-300">Good when:</span> {m.good_when}</p>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}

import React from "react";

// Highlights the scannable bits inside narrative prose so dense text reads fast:
//   • signed numbers / percentages → colored (green up ▲ / red down ▼)
//   • dollar amounts and magnitudes (e.g. $10.8B, 2.6M, 60%) → bold
//   • known ticker symbols → bold
// Everything else stays plain. Purely presentational; the text itself is unchanged.
const TOKEN =
  /(?<![A-Za-z0-9])([+\-−]\$?\d[\d,]*(?:\.\d+)?\s?(?:%|pp|bps|x|bn|B|M|k)?)|(\$\d[\d,]*(?:\.\d+)?\s?(?:bn|B|M|k|trillion|billion|million)?)|(\b\d[\d,]*(?:\.\d+)?\s?(?:%|pp|bps|x|bn|B|M|k))|(\b[A-Z]{2,5}\b)/g;

// Direction words let us color an UNSIGNED return ("down 11.3%", "up about 7%")
// the way a signed one (+/-) is already colored. We look at the word immediately
// before the number, skipping filler ("about", "roughly", "to"), and color only
// when that word is unambiguously directional.
const DOWN = new Set(
  "down fell fall falls dropped drop drops lost lose loses lower off slid slide slides sank sink sinks declined decline declines plunged plunge tumbled tumble shed sheds sliding falling dropping losing slipped slip slips slipping sold selling sells retreated sank cratered".split(" "),
);
const UP = new Set(
  "up rose rise rises gained gain gains jumped jump jumps higher climbed climb climbs added adds surged surge surges popped pop pops rallied rally rallies advanced advance advances rising gaining climbing soared soar jumping".split(" "),
);
const FILLER = new Set(
  "about around roughly nearly approximately by another still now is are was were to a an of almost over some only just more than".split(" "),
);

function directionBefore(pre: string): "down" | "up" | null {
  const words = pre.toLowerCase().replace(/[^a-z\s]/g, " ").trim().split(/\s+/).filter(Boolean);
  let w = words.pop();
  while (w && FILLER.has(w)) w = words.pop();
  if (!w) return null;
  if (DOWN.has(w)) return "down";
  if (UP.has(w)) return "up";
  return null;
}

export default function RichText({
  text,
  symbols = [],
}: {
  text?: string | null;
  symbols?: string[];
}) {
  if (!text) return null;
  // Stopgap: render em-dashes as commas (the routine is also instructed not to write them).
  text = text.replace(/\s*—\s*/g, ", ");
  const known = new Set(symbols.map((s) => s.toUpperCase()));
  const nodes: React.ReactNode[] = [];
  let last = 0;
  let k = 0;
  let m: RegExpExecArray | null;
  TOKEN.lastIndex = 0;
  while ((m = TOKEN.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index));
    const [full, signed, dollar, mag, ticker] = m;
    if (signed) {
      const down = /^[-−]/.test(signed);
      const body = signed.replace(/^[+\-−]\s?/, "");
      nodes.push(
        <span key={k++} className={`whitespace-nowrap font-semibold ${down ? "text-rose-400" : "text-emerald-400"}`}>
          {down ? "▼" : "▲"} {body}
        </span>,
      );
    } else if (dollar || mag) {
      const dir = directionBefore(text.slice(Math.max(0, m.index - 40), m.index));
      if (dir) {
        const down = dir === "down";
        nodes.push(
          <span key={k++} className={`whitespace-nowrap font-semibold ${down ? "text-rose-400" : "text-emerald-400"}`}>
            {down ? "▼" : "▲"} {dollar || mag}
          </span>,
        );
      } else {
        nodes.push(
          <span key={k++} className="font-semibold text-zinc-100">
            {dollar || mag}
          </span>,
        );
      }
    } else if (ticker) {
      if (known.has(ticker)) {
        nodes.push(
          <span key={k++} className="font-semibold text-zinc-100">
            {ticker}
          </span>,
        );
      } else {
        nodes.push(ticker);
      }
    }
    last = m.index + full.length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return <>{nodes}</>;
}

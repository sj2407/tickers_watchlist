import React from "react";

// Highlights the scannable bits inside narrative prose so dense text reads fast:
//   • signed numbers / percentages → colored (green up ▲ / red down ▼)
//   • dollar amounts and magnitudes (e.g. $10.8B, 2.6M, 60%) → bold
//   • known ticker symbols → bold
// Everything else stays plain. Purely presentational; the text itself is unchanged.
const TOKEN =
  /(?<![A-Za-z0-9])([+\-−]\$?\d[\d,]*(?:\.\d+)?\s?(?:%|pp|bps|x|bn|B|M|k)?)|(\$\d[\d,]*(?:\.\d+)?\s?(?:bn|B|M|k|trillion|billion|million)?)|(\b\d[\d,]*(?:\.\d+)?\s?(?:%|pp|bps|x|bn|B|M|k))|(\b[A-Z]{2,5}\b)/g;

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
      nodes.push(
        <span key={k++} className="font-semibold text-zinc-100">
          {dollar || mag}
        </span>,
      );
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

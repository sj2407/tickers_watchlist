// Live quotes for the book-value total ONLY. Finnhub /quote covers US names and
// ADRs alike, one cheap call per symbol, cached 60s by the Next Data Cache so a
// burst of page loads can't exceed ~1 fetch/name/minute. Everything narrative on
// the page stays priced at the snapshot timestamp — only the money number goes live.
//
// Needs FINNHUB_API_KEY in the environment. With no key (or on any failure) this
// returns {} and the book falls back to snapshot prices — never a broken number.

const FINNHUB_QUOTE = "https://finnhub.io/api/v1/quote";

export interface LiveQuote {
  price: number;
  t: number; // Finnhub quote epoch seconds
}

export async function getLiveQuotes(
  symbols: string[],
): Promise<{ quotes: Record<string, LiveQuote>; asOf: number | null }> {
  const key = process.env.FINNHUB_API_KEY;
  if (!key || symbols.length === 0) return { quotes: {}, asOf: null };

  const quotes: Record<string, LiveQuote> = {};
  let asOf: number | null = null;

  await Promise.all(
    symbols.map(async (sym) => {
      try {
        const res = await fetch(`${FINNHUB_QUOTE}?symbol=${encodeURIComponent(sym)}&token=${key}`, {
          next: { revalidate: 60 },
        });
        if (!res.ok) return;
        const d = (await res.json()) as { c?: number; t?: number };
        // Finnhub returns c=0 for unknown symbols / no data — treat as missing.
        const price = typeof d.c === "number" && Number.isFinite(d.c) && d.c > 0 ? d.c : null;
        if (price == null) return;
        quotes[sym] = { price, t: typeof d.t === "number" ? d.t : 0 };
        if (d.t && (asOf == null || d.t > asOf)) asOf = d.t;
      } catch {
        // skip this symbol; the book falls back to its snapshot price
      }
    }),
  );

  return { quotes, asOf };
}

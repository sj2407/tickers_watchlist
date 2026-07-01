import { promises as fs } from "fs";
import path from "path";
import { sql, hasDb } from "./db";
import type { Snapshot, Lean } from "./types";

// Offline-dev fallback: the pipeline's working file (repo root is one level up).
const REPO_ROOT = path.join(process.cwd(), "..");
const SNAPSHOT_FILE = path.join(REPO_ROOT, "out", "snapshot.json");

export interface CurrentPosition {
  ticker: string;
  shares: number;
  avg_cost: number | null;
  invested: number | null;
  realized_pl: number | null;
}

/** Latest snapshot: from Postgres if available, else the pipeline's JSON file. */
export async function getLatestSnapshot(): Promise<Snapshot | null> {
  if (hasDb && sql) {
    // Prefer the latest ENRICHED snapshot (market_recap set) so an in-flight insert
    // never flashes a dry, narration-less board; fall back to latest if none enriched yet.
    const rows = await sql<{ payload: Snapshot }[]>`
      SELECT payload FROM snapshots
      WHERE payload->>'market_recap' IS NOT NULL
      ORDER BY generated_at DESC LIMIT 1
    `;
    if (rows.length) return rows[0].payload;
    const fallback = await sql<{ payload: Snapshot }[]>`
      SELECT payload FROM snapshots ORDER BY generated_at DESC LIMIT 1
    `;
    return fallback.length ? fallback[0].payload : null;
  }
  try {
    return JSON.parse(await fs.readFile(SNAPSHOT_FILE, "utf8")) as Snapshot;
  } catch {
    return null;
  }
}

export async function getTicker(symbol: string) {
  const snap = await getLatestSnapshot();
  if (!snap) return null;
  return snap.tickers.find((t) => t.ticker === symbol.toUpperCase()) ?? null;
}

export interface LeanHistoryPoint {
  generated_at: string;
  as_of_date: string;
  mode: string | null;
  final_lean: Lean | null;
  provisional_lean: Lean | null;
}

/** Per-run lean history for one name, newest first. Extracts just this ticker's quant
 *  proposal + final call out of each enriched snapshot payload (server-side, so we never
 *  ship 30 full snapshots to the client) — so a flip like hold→trim is visible over time.
 *  Empty in file mode (only the single working snapshot exists there). */
export async function getLeanHistory(symbol: string, limit = 40): Promise<LeanHistoryPoint[]> {
  if (!(hasDb && sql)) return [];
  const sym = symbol.toUpperCase();
  return sql<LeanHistoryPoint[]>`
    SELECT
      generated_at::text AS generated_at,
      as_of_date::text   AS as_of_date,
      mode,
      jsonb_path_query_first(
        payload, '$.tickers[*] ? (@.ticker == $s).final_lean',
        jsonb_build_object('s', ${sym}::text)) #>> '{}' AS final_lean,
      jsonb_path_query_first(
        payload, '$.tickers[*] ? (@.ticker == $s).signals.provisional_lean',
        jsonb_build_object('s', ${sym}::text)) #>> '{}' AS provisional_lean
    FROM snapshots
    WHERE payload->>'market_recap' IS NOT NULL
    ORDER BY generated_at DESC
    LIMIT ${limit}
  `;
}

export interface TradeRow {
  executed_at: string;
  side: "buy" | "sell";
  shares: number;
  price: number;
  amount: number; // shares * price, unsigned dollars
  note: string;
}

/** Every recorded trade for one name, oldest first — feeds the trade-history list and
 *  the position-vs-price chart. Empty in file mode (the ledger lives in Postgres). */
export async function getTradeHistory(symbol: string): Promise<TradeRow[]> {
  if (!(hasDb && sql)) return [];
  return sql<TradeRow[]>`
    SELECT executed_at::text AS executed_at, side, shares, price,
           (shares * price)::float AS amount, note
    FROM transactions
    WHERE ticker = ${symbol.toUpperCase()}
    ORDER BY executed_at ASC
  `;
}

/** Live derived positions from the transaction ledger (Postgres only). */
export async function getCurrentPositions(): Promise<Record<string, CurrentPosition>> {
  if (!(hasDb && sql)) return {};
  const rows = await sql<CurrentPosition[]>`
    SELECT ticker, shares, avg_cost, invested, realized_pl
    FROM current_positions WHERE shares > 0
  `;
  const out: Record<string, CurrentPosition> = {};
  for (const r of rows) out[r.ticker.toUpperCase()] = r;
  return out;
}

export interface LivePos {
  ticker: string;
  held: boolean;
  shares: number;
  cost_basis: number | null;
  invested: number | null;
  market_value: number | null;
  unrealized_pl: number | null;
  since_entry_pct: number | null;
  weight_pct: number | null;
}

/** Live position math straight from the transaction ledger + prices.
 * Shares/avg-cost/invested reflect your trades INSTANTLY (no pipeline run needed).
 * Prices: a live quote from `livePrices` when present (per symbol), otherwise the
 * snapshot's last price. `livePriced` is true if at least one live price was used.
 * Pass no `livePrices` (the default) to keep everything at snapshot prices. Empty in
 * file mode (no ledger). */
export async function getLivePositions(
  snap: Snapshot | null,
  livePrices: Record<string, number> = {},
): Promise<{ book: number; byTicker: Record<string, LivePos>; livePriced: boolean }> {
  const positions = await getCurrentPositions();
  const snapPrice: Record<string, number | null> = {};
  for (const t of snap?.tickers ?? []) snapPrice[t.ticker] = t.price?.last ?? null;

  let book = 0;
  let livePriced = false;
  const byTicker: Record<string, LivePos> = {};
  for (const [sym, p] of Object.entries(positions)) {
    const live = livePrices[sym];
    const hasLive = typeof live === "number" && Number.isFinite(live) && live > 0;
    if (hasLive) livePriced = true;
    const last = hasLive ? live : (snapPrice[sym] ?? null);
    const mv = last != null ? p.shares * last : null;
    if (mv != null) book += mv;
    byTicker[sym] = {
      ticker: sym, held: p.shares > 0, shares: p.shares, cost_basis: p.avg_cost, invested: p.invested,
      market_value: mv,
      unrealized_pl: mv != null && p.invested != null ? mv - p.invested : null,
      since_entry_pct: last != null && p.avg_cost ? (last / p.avg_cost - 1) * 100 : null,
      weight_pct: null,
    };
  }
  for (const v of Object.values(byTicker)) {
    v.weight_pct = v.market_value != null && book ? (v.market_value / book) * 100 : null;
  }
  return { book, byTicker, livePriced };
}

/** Record a trade in the append-only ledger. side: 'buy' (size up) | 'sell' (trim). */
export async function addTransaction(t: {
  ticker: string;
  side: "buy" | "sell";
  shares: number;
  price: number;
  note?: string;
}): Promise<void> {
  if (!(hasDb && sql)) {
    throw new Error("No database configured. Transactions require DATABASE_URL.");
  }
  await sql`
    INSERT INTO transactions (ticker, side, shares, price, source, note)
    VALUES (${t.ticker.toUpperCase()}, ${t.side}, ${t.shares}, ${t.price}, 'app', ${t.note ?? ""})
  `;
}

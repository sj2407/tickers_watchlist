import { promises as fs } from "fs";
import path from "path";
import { sql, hasDb } from "./db";
import type { Snapshot } from "./types";

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

/** Live position math straight from the transaction ledger + latest snapshot prices.
 * Shares/avg-cost/invested reflect your trades INSTANTLY (no pipeline run needed);
 * value/P&L/weight are priced at the snapshot's last price. Empty in file mode (no ledger). */
export async function getLivePositions(
  snap: Snapshot | null,
): Promise<{ book: number; byTicker: Record<string, LivePos> }> {
  const positions = await getCurrentPositions();
  const priceOf: Record<string, number | null> = {};
  for (const t of snap?.tickers ?? []) priceOf[t.ticker] = t.price?.last ?? null;

  let book = 0;
  const byTicker: Record<string, LivePos> = {};
  for (const [sym, p] of Object.entries(positions)) {
    const last = priceOf[sym] ?? null;
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
  return { book, byTicker };
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

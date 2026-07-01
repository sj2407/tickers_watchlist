"use server";

import { revalidatePath } from "next/cache";
import { addTransaction, getCurrentPositions } from "@/lib/data";

export type TradeInput = {
  ticker: string;
  side: "buy" | "sell";
  shares: number;
  price: number;
  note?: string;
};

/**
 * Record a buy/sell in the ledger as a Server Action (not a Route Handler) so the
 * whole app's client Router Cache is invalidated: the ticker page AND the board's
 * book-value total both pick up the new share count on the next navigation. A bare
 * fetch() to a Route Handler only revalidates the current route, which is why the
 * board total used to lag the per-ticker shares after a trade.
 */
export type TradePosition = { shares: number; avg_cost: number | null; invested: number | null };

export async function recordTrade(
  input: TradeInput,
): Promise<{ ok: boolean; error?: string; position?: TradePosition }> {
  if (!input?.ticker || (input.side !== "buy" && input.side !== "sell")) {
    return { ok: false, error: "ticker and side (buy|sell) required" };
  }
  if (!(typeof input.shares === "number" && input.shares > 0) || !(typeof input.price === "number" && input.price >= 0)) {
    return { ok: false, error: "positive shares and price required" };
  }
  try {
    await addTransaction(input);
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
  // "layout" at the root invalidates every page (board + all ticker pages), so the
  // book-value total and per-name shares can never disagree after a trade.
  revalidatePath("/", "layout");
  // Read back the derived position so the client can confirm the trade with real
  // numbers (a full exit drops out of current_positions → report shares 0).
  let position: TradePosition | undefined;
  try {
    const p = (await getCurrentPositions())[input.ticker.toUpperCase()];
    position = p
      ? { shares: p.shares, avg_cost: p.avg_cost, invested: p.invested }
      : { shares: 0, avg_cost: null, invested: null };
  } catch {
    /* confirmation numbers are best-effort; the trade itself already succeeded */
  }
  return { ok: true, position };
}

"use server";

import { revalidatePath } from "next/cache";
import { addTransaction } from "@/lib/data";

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
export async function recordTrade(input: TradeInput): Promise<{ ok: boolean; error?: string }> {
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
  return { ok: true };
}

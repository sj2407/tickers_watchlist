import { NextRequest, NextResponse } from "next/server";
import { getCurrentPositions, addTransaction } from "@/lib/data";

// GET → live derived positions (so the editor can show the up-to-date holding).
export async function GET() {
  return NextResponse.json(await getCurrentPositions());
}

// POST → record a buy (size up) or sell (trim) in the ledger.
export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => null)) as {
    ticker?: string;
    side?: "buy" | "sell";
    shares?: number;
    price?: number;
    note?: string;
  } | null;

  if (!body?.ticker || (body.side !== "buy" && body.side !== "sell")) {
    return NextResponse.json({ ok: false, error: "ticker and side (buy|sell) required" }, { status: 400 });
  }
  if (typeof body.shares !== "number" || body.shares <= 0 || typeof body.price !== "number" || body.price < 0) {
    return NextResponse.json({ ok: false, error: "positive shares and price required" }, { status: 400 });
  }

  try {
    await addTransaction({ ticker: body.ticker, side: body.side, shares: body.shares, price: body.price, note: body.note });
  } catch (e) {
    return NextResponse.json({ ok: false, error: (e as Error).message }, { status: 500 });
  }
  return NextResponse.json({ ok: true });
}

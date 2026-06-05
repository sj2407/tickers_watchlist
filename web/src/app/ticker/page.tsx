import { redirect } from "next/navigation";
import { getLatestSnapshot, getLivePositions } from "@/lib/data";
import { tickerOrder } from "@/lib/order";

export const dynamic = "force-dynamic";

// The "Tickers" tab has no symbol of its own — land on the first held name in the
// attention order (else the first name on the board).
export default async function TickerIndex() {
  const snap = await getLatestSnapshot();
  if (!snap || snap.tickers.length === 0) redirect("/");
  const { byTicker } = await getLivePositions(snap);
  const heldSet = new Set(
    snap.tickers.filter((t) => byTicker[t.ticker]?.held ?? t.position.held).map((t) => t.ticker),
  );
  const { order } = tickerOrder(snap, heldSet);
  redirect(`/ticker/${order[0] ?? snap.tickers[0].ticker}`);
}

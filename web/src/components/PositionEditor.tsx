"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Position } from "@/lib/types";
import { usd } from "@/lib/format";

// Records a BUY (size up) or SELL (trim) in the ledger at the current price.
// Average cost is derived server-side, so there's nothing to type by hand.
// Enforces the $200 floor: a trim can't leave a position worth < $200 (but a
// full exit to $0 is allowed).
export default function PositionEditor({
  ticker,
  position,
  lastPrice,
  minPositionUsd,
}: {
  ticker: string;
  position: Position;
  lastPrice: number | null;
  minPositionUsd: number;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [amount, setAmount] = useState(200);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const shares = position.shares ?? 0;
  const value = position.market_value ?? (lastPrice ? shares * lastPrice : 0);
  const canTrade = lastPrice != null && lastPrice > 0;

  const projAfterBuy = value + amount;
  const projAfterSell = Math.max(0, value - amount);
  const sellLeavesBelowFloor = projAfterSell > 0 && projAfterSell < minPositionUsd;
  const sellMoreThanHeld = amount > value + 0.01;

  async function trade(side: "buy" | "sell") {
    if (!canTrade) return;
    if (side === "sell" && sellLeavesBelowFloor) {
      setMsg(`A $${amount} trim would leave ${usd(projAfterSell)} — below the $${minPositionUsd} floor. Trim less, or exit fully.`);
      return;
    }
    let dShares = amount / lastPrice!;
    if (side === "sell") dShares = Math.min(dShares, shares); // can't sell more than held
    setBusy(true);
    setMsg(null);
    const res = await fetch("/api/transactions", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ ticker, side, shares: +dShares.toFixed(6), price: lastPrice, note: `${side} $${amount} via app` }),
    });
    setBusy(false);
    if (res.ok) {
      setMsg(`${side === "buy" ? "Added" : "Trimmed"} ${usd(amount, 0)}. Numbers refresh on the next data run.`);
      router.refresh();
    } else {
      setMsg("Save failed.");
    }
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)}
        className="rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-200 ring-1 ring-zinc-700 hover:bg-zinc-700">
        Trim / add
      </button>
    );
  }

  return (
    <div className="mt-3 space-y-3 rounded-xl bg-zinc-950/60 p-4 ring-1 ring-zinc-800">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-zinc-200">Trade {ticker}</span>
        <button onClick={() => setOpen(false)} className="text-xs text-zinc-500">close</button>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-xs text-zinc-400">Amount</span>
        <div className="flex gap-1">
          {[100, 200, 500].map((a) => (
            <button key={a} onClick={() => setAmount(a)}
              className={`rounded-md px-2 py-1 text-xs ring-1 ${amount === a ? "bg-sky-500/20 text-sky-200 ring-sky-500/40" : "bg-zinc-900 text-zinc-300 ring-zinc-800"}`}>
              ${a}
            </button>
          ))}
        </div>
        <input type="number" min={1} step={1} value={amount}
          onChange={(e) => setAmount(Math.max(1, Number(e.target.value)))}
          className="w-20 rounded-md bg-zinc-900 px-2 py-1 text-sm text-zinc-100 ring-1 ring-zinc-800" />
      </div>

      <div className="flex gap-2">
        <button disabled={busy || !canTrade} onClick={() => trade("buy")}
          className="flex-1 rounded-lg bg-emerald-500/15 px-3 py-2 text-sm font-medium text-emerald-300 ring-1 ring-emerald-500/30 disabled:opacity-40">
          + Add {usd(amount, 0)}
        </button>
        <button disabled={busy || !canTrade || shares <= 0 || sellMoreThanHeld} onClick={() => trade("sell")}
          className="flex-1 rounded-lg bg-amber-500/15 px-3 py-2 text-sm font-medium text-amber-300 ring-1 ring-amber-500/30 disabled:opacity-40">
          − Trim {usd(amount, 0)}
        </button>
      </div>

      <div className="text-xs text-zinc-500">
        Now {usd(value)} · after add {usd(projAfterBuy)} · after trim {usd(projAfterSell)}
        {sellLeavesBelowFloor && <span className="ml-1 text-rose-400">(trim below ${minPositionUsd} floor)</span>}
      </div>
      {msg && <p className="text-xs text-zinc-300">{msg}</p>}
    </div>
  );
}

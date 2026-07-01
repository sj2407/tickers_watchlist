"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { usd, num } from "@/lib/format";
import { recordTrade } from "@/app/actions";

// Only the fields the editor reads — satisfied by both Position and LivePos.
type EditablePosition = {
  shares?: number;
  cost_basis?: number | null;
  market_value?: number | null;
};

// Records a BUY (size up) or SELL (trim) in the ledger at the current price.
// Average cost is derived server-side, so there's nothing to type by hand.
// Enforces the $200 floor: a trim can't leave a position worth < $200 (but a
// full exit to $0 is allowed).
export default function PositionEditor({
  ticker,
  position,
  lastPrice,
  minPositionUsd,
  open: openProp,
  onOpenChange,
  showTrigger = true,
}: {
  ticker: string;
  position: EditablePosition;
  lastPrice: number | null;
  minPositionUsd: number;
  open?: boolean;
  onOpenChange?: (b: boolean) => void;
  showTrigger?: boolean;
}) {
  const router = useRouter();
  const [internalOpen, setInternalOpen] = useState(false);
  const open = openProp !== undefined ? openProp : internalOpen;
  const setOpen = (b: boolean) => (onOpenChange ? onOpenChange(b) : setInternalOpen(b));
  const [amount, setAmount] = useState(200);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  // A prominent, self-dismissing confirmation of the last trade (so a fill is an
  // *event*, not a silent number change you have to hunt for).
  const [toast, setToast] = useState<string | null>(null);
  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(null), 7000);
    return () => clearTimeout(id);
  }, [toast]);

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
      setMsg(`A $${amount} trim would leave ${usd(projAfterSell)}, below the $${minPositionUsd} floor. Trim less, or exit fully.`);
      return;
    }
    let dShares = amount / lastPrice!;
    if (side === "sell") dShares = Math.min(dShares, shares); // can't sell more than held
    setBusy(true);
    setMsg(null);
    const res = await recordTrade({ ticker, side, shares: +dShares.toFixed(6), price: lastPrice, note: `${side} $${amount} via app` });
    setBusy(false);
    if (res.ok) {
      const p = res.position;
      const posPart = p && p.shares > 0
        ? `Position now ${num(p.shares, 2)} sh${p.avg_cost != null ? `, avg cost ${usd(p.avg_cost)}` : ""}.`
        : "Position fully closed.";
      setToast(`${side === "buy" ? "Added" : "Trimmed"} ${usd(amount, 0)} · ${num(+dShares.toFixed(4), 4)} sh @ ${usd(lastPrice!)}. ${posPart}`);
      setMsg(null);
      router.refresh();
    } else {
      setMsg(res.error ? `Save failed: ${res.error}` : "Save failed.");
    }
  }

  // Fixed, dismissible confirmation shown after a fill — survives the router.refresh()
  // (client state is preserved) and auto-hides. Rendered from both editor states.
  const toastEl = toast ? (
    <div className="fixed bottom-4 right-4 z-50 max-w-sm animate-in fade-in slide-in-from-bottom-2">
      <div className="flex items-start gap-3 rounded-xl bg-zinc-900 p-3 text-sm text-zinc-100 shadow-lg ring-1 ring-emerald-500/40">
        <span className="mt-0.5 grid h-5 w-5 flex-none place-items-center rounded-full bg-emerald-500/20 text-[11px] text-emerald-300">✓</span>
        <p className="leading-snug">{toast}</p>
        <button onClick={() => setToast(null)} className="ml-1 flex-none text-zinc-500 hover:text-zinc-300" aria-label="Dismiss">✕</button>
      </div>
    </div>
  ) : null;

  if (!open) {
    if (!showTrigger) return toastEl;
    return (
      <>
        {toastEl}
        <button onClick={() => setOpen(true)}
          className="rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-200 ring-1 ring-zinc-700 hover:bg-zinc-700">
          Trim / add
        </button>
      </>
    );
  }

  return (
    <>
    {toastEl}
    <div className="mt-3 space-y-3 rounded-xl bg-zinc-950/60 p-4 ring-1 ring-zinc-800">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-zinc-200">Trade {ticker}</span>
        <button onClick={() => setOpen(false)} className="text-xs text-zinc-400">close</button>
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
    </>
  );
}

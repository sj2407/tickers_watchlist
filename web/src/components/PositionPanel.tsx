"use client";
import { useState } from "react";
import { Metric } from "@/components/ui";
import { usd, pct, num, signClass } from "@/lib/format";
import PositionEditor from "@/components/PositionEditor";

type Pos = {
  held: boolean;
  shares: number;
  cost_basis: number | null;
  invested: number | null;
  market_value: number | null;
  unrealized_pl: number | null;
  since_entry_pct: number | null;
  weight_pct: number | null;
};

// The "Your position" card: compact header with the Trim/add button beside it (no
// separate row), the live metrics, and the editor panel that expands below.
export default function PositionPanel({
  ticker,
  pos,
  lastPrice,
  minPos,
}: {
  ticker: string;
  pos: Pos;
  lastPrice: number | null;
  minPos: number;
}) {
  const [open, setOpen] = useState(false);
  return (
    <section className="rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
      <div className="mb-3 flex items-center gap-2">
        <span className="h-4 w-1 rounded-full bg-emerald-500/70" />
        <h2 className="text-sm font-semibold text-zinc-100">Your position</h2>
        <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-medium text-emerald-300">● live</span>
        {lastPrice != null && (
          <button
            onClick={() => setOpen((o) => !o)}
            className="ml-auto rounded-lg bg-zinc-800 px-2.5 py-1 text-xs text-zinc-200 ring-1 ring-zinc-700 hover:bg-zinc-700"
          >
            {open ? "Close" : pos.held ? "Trim / add" : "Add shares"}
          </button>
        )}
      </div>
      {pos.held ? (
        <div className="grid grid-cols-3 gap-3">
          <Metric label="Shares" value={num(pos.shares, 4)} />
          <Metric label="Value" value={usd(pos.market_value)} hint="at last price" />
          <Metric label="Invested" value={usd(pos.invested)} />
          <Metric label="Gain/loss" value={usd(pos.unrealized_pl)} className={signClass(pos.unrealized_pl)} hint="unrealized" />
          <Metric label="Since entry" value={pct(pos.since_entry_pct)} className={signClass(pos.since_entry_pct)} />
          <Metric label="Weight" value={pct(pos.weight_pct, 0)} hint="of book" />
        </div>
      ) : (
        <p className="text-sm text-zinc-400">Watch-only. Add shares to start tracking P/L.</p>
      )}
      {lastPrice != null && (
        <PositionEditor
          ticker={ticker}
          position={pos}
          lastPrice={lastPrice}
          minPositionUsd={minPos}
          open={open}
          onOpenChange={setOpen}
          showTrigger={false}
        />
      )}
    </section>
  );
}

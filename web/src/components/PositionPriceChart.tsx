"use client";
import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  LineSeries,
  HistogramSeries,
  type IChartApi,
  type Time,
} from "lightweight-charts";
import type { PricePoint } from "@/lib/types";
import type { TradeRow } from "@/lib/data";
import { SectionHeader } from "@/components/ui";

// yyyy-mm-dd in exchange-local (ET) terms, so a trade timestamp lines up with the daily
// price series. (Price is a daily close, so intraday timing isn't captured — that's fine.)
function toDay(iso: string): string {
  return new Date(iso).toLocaleDateString("en-CA", { timeZone: "America/New_York" });
}

// Your trades over the price. Bars (left axis) are dollars added (green) / trimmed
// (amber) per day; the line (right axis) is price; arrows pin each fill to the price it
// happened at — so you can review whether you added into strength or trimmed into it.
export default function PositionPriceChart({ series, trades }: { series: PricePoint[]; trades: TradeRow[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || series.length === 0 || trades.length === 0) return;
    const chart: IChartApi = createChart(ref.current, {
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#a1a1aa", attributionLogo: false },
      grid: { vertLines: { color: "rgba(63,63,70,0.25)" }, horzLines: { color: "rgba(63,63,70,0.25)" } },
      rightPriceScale: { borderColor: "rgba(63,63,70,0.4)", visible: true },
      leftPriceScale: { borderColor: "rgba(63,63,70,0.4)", visible: true },
      timeScale: { borderColor: "rgba(63,63,70,0.4)", timeVisible: false },
      crosshair: { mode: 1 },
      autoSize: true,
    });

    // Price — right axis.
    const price = chart.addSeries(LineSeries, { color: "#38bdf8", lineWidth: 2, priceScaleId: "right", priceLineVisible: false });
    price.setData(series.map((p) => ({ time: p.t as Time, value: p.c })));

    // Trade dollars — left axis, one bar per day (net signed: adds up, trims down).
    const byDay = new Map<string, number>();
    for (const t of trades) {
      const d = toDay(t.executed_at);
      byDay.set(d, (byDay.get(d) ?? 0) + (t.side === "buy" ? t.amount : -t.amount));
    }
    const bars = [...byDay.entries()]
      .sort((a, b) => (a[0] < b[0] ? -1 : 1))
      .map(([time, v]) => ({ time: time as Time, value: v, color: v >= 0 ? "rgba(52,211,153,0.6)" : "rgba(251,191,36,0.6)" }));
    const hist = chart.addSeries(HistogramSeries, {
      priceScaleId: "left",
      base: 0,
      priceFormat: { type: "price", precision: 0, minMove: 1 },
      // No last-value tag / dotted price line — the bar height already reads off the
      // left axis; the extra label just clutters the plot (review: overlapping labels).
      lastValueVisible: false,
      priceLineVisible: false,
    });
    hist.setData(bars);

    // No price-line markers: the colored bars already sit on the trade dates and encode
    // amount + direction, and the trade-history list has the exact price. Arrows on the
    // line only added clutter.

    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [series, trades]);

  if (series.length === 0 || trades.length === 0) return null;

  return (
    <section className="mt-4 rounded-2xl bg-zinc-900/70 p-4 ring-1 ring-zinc-800">
      <SectionHeader title="Your trades vs price" accent="emerald" />
      <p className="mb-2 text-[11px] leading-relaxed text-zinc-500">
        Bars are dollars added (green) or trimmed (amber) that day (left axis); the line is price (right axis). Hover a bar for the exact amount, or see the trade log below. Price is a daily close, so intraday timing isn&apos;t exact.
      </p>
      <div ref={ref} className="h-64 w-full sm:h-72" />
    </section>
  );
}

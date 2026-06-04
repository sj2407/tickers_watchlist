"use client";
import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  CandlestickSeries,
  LineSeries,
  type IChartApi,
} from "lightweight-charts";
import type { PricePoint } from "@/lib/types";

// Simple moving average over close prices.
function sma(points: PricePoint[], period: number) {
  const out: { time: string; value: number }[] = [];
  for (let i = period - 1; i < points.length; i++) {
    let s = 0;
    for (let j = i - period + 1; j <= i; j++) s += points[j].c;
    out.push({ time: points[i].t, value: +(s / period).toFixed(2) });
  }
  return out;
}

export default function PriceChart({ series }: { series: PricePoint[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || series.length === 0) return;
    const chart: IChartApi = createChart(ref.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#a1a1aa",
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "rgba(63,63,70,0.25)" },
        horzLines: { color: "rgba(63,63,70,0.25)" },
      },
      rightPriceScale: { borderColor: "rgba(63,63,70,0.4)" },
      timeScale: { borderColor: "rgba(63,63,70,0.4)", timeVisible: false },
      crosshair: { mode: 1 },
      autoSize: true,
      handleScroll: true,
      handleScale: true,
    });

    const candles = chart.addSeries(CandlestickSeries, {
      upColor: "#34d399",
      downColor: "#fb7185",
      borderVisible: false,
      wickUpColor: "#34d399",
      wickDownColor: "#fb7185",
    });
    candles.setData(
      series.map((p) => ({ time: p.t, open: p.o, high: p.h, low: p.l, close: p.c })),
    );

    if (series.length >= 50) {
      const ma50 = chart.addSeries(LineSeries, { color: "#38bdf8", lineWidth: 1 });
      ma50.setData(sma(series, 50));
    }

    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [series]);

  if (series.length === 0)
    return <div className="h-64 grid place-items-center text-sm text-zinc-500">No price history</div>;

  return <div ref={ref} className="h-64 w-full sm:h-80" />;
}

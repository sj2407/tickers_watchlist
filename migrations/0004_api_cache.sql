-- 0004 — per-ET-trading-day cache for slow Finnhub data (earnings calendar + analyst only).
-- Fundamentals are NOT cached here (they live in the `fundamentals` table — one owner per datum).
CREATE TABLE IF NOT EXISTS api_cache (
  cache_key   text PRIMARY KEY,
  payload     jsonb NOT NULL,
  trading_day date  NOT NULL,
  fetched_at  timestamptz NOT NULL DEFAULT now()
);

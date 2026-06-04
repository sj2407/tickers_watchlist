-- 0001_init — future-proof core schema for tickers_watchlist.
-- Standard Postgres (no vendor extensions) so it runs on local PG / Neon / Supabase.

-- Which tickers we track + per-name metadata (editable from the app).
CREATE TABLE IF NOT EXISTS watchlist (
  ticker      text PRIMARY KEY,
  active      boolean          NOT NULL DEFAULT true,
  sector_etf  text,
  target      double precision,
  stop        double precision,
  notes       text             NOT NULL DEFAULT '',
  added_at    timestamptz      NOT NULL DEFAULT now()
);

-- Append-only trade ledger. Positions are DERIVED from this — we never mutate
-- a cost-basis field in place. Buys = size up, sells = trim.
CREATE TABLE IF NOT EXISTS transactions (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ticker      text             NOT NULL,
  side        text             NOT NULL CHECK (side IN ('buy','sell')),
  shares      double precision NOT NULL CHECK (shares > 0),
  price       double precision NOT NULL CHECK (price >= 0),
  fees        double precision NOT NULL DEFAULT 0,
  executed_at timestamptz      NOT NULL DEFAULT now(),
  source      text             NOT NULL DEFAULT 'app',   -- app | seed | import
  note        text             NOT NULL DEFAULT '',
  created_at  timestamptz      NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS transactions_ticker_idx ON transactions (ticker, executed_at);

-- Time-series of each routine run's full (enriched) payload.
CREATE TABLE IF NOT EXISTS snapshots (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  generated_at timestamptz NOT NULL,
  mode         text        NOT NULL CHECK (mode IN ('preopen','postclose')),
  as_of_date   date        NOT NULL,
  payload      jsonb       NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS snapshots_generated_idx ON snapshots (generated_at DESC);

-- Current position per ticker, average-cost method, derived from the ledger.
-- avg_cost = cost per share across all buys; selling reduces share count, not avg cost.
CREATE OR REPLACE VIEW current_positions AS
WITH agg AS (
  SELECT
    ticker,
    COALESCE(SUM(shares)            FILTER (WHERE side = 'buy'),  0) AS buy_sh,
    COALESCE(SUM(shares)            FILTER (WHERE side = 'sell'), 0) AS sell_sh,
    COALESCE(SUM(shares*price+fees) FILTER (WHERE side = 'buy'),  0) AS buy_cost,
    COALESCE(SUM(shares*price-fees) FILTER (WHERE side = 'sell'), 0) AS sell_proceeds
  FROM transactions
  GROUP BY ticker
)
SELECT
  ticker,
  (buy_sh - sell_sh)                                              AS shares,
  CASE WHEN buy_sh > 0 THEN buy_cost / buy_sh END                 AS avg_cost,
  (buy_sh - sell_sh) * CASE WHEN buy_sh > 0 THEN buy_cost/buy_sh ELSE 0 END AS invested,
  sell_proceeds - sell_sh * CASE WHEN buy_sh > 0 THEN buy_cost/buy_sh ELSE 0 END AS realized_pl
FROM agg;

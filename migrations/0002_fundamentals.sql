-- 0002 — cached quarterly fundamentals (refreshed weekly + on earnings, not every run).
CREATE TABLE IF NOT EXISTS fundamentals (
  ticker               text PRIMARY KEY,
  report_date          date,
  fiscal_period        text,
  revenue              double precision,
  revenue_yoy          double precision,
  revenue_qoq_pct      double precision,
  eps                  double precision,
  eps_yoy              double precision,
  eps_ttm              double precision,
  gross_margin         double precision,
  gross_margin_qoq_pp  double precision,
  eps_miss_count_last3 integer,
  source               text,
  fetched_at           timestamptz NOT NULL DEFAULT now()
);

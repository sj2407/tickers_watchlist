-- 0005 — intraday alert dedup (once per ticker/trigger/ET day), idempotent.
CREATE TABLE IF NOT EXISTS intraday_alerts (
  ticker     text NOT NULL,
  trigger    text NOT NULL,
  alert_date date NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, trigger, alert_date)
);

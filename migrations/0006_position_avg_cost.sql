-- 0006 — correct average-cost math for current_positions.
--
-- The 0001 view computed avg_cost = all-time buy cost / all-time shares bought,
-- which is wrong after any sell-then-rebuy (a later buy must re-average over the
-- REMAINING shares only, and a full exit must reset the average), and computed
-- realized P/L against the final overall average (order-independent, retroactive).
--
-- This version folds the ledger chronologically per ticker (recursive CTE):
--   buy : shares += s; cost += s*price + fees                (avg re-averages)
--   sell: matched = LEAST(s, shares);
--         realized += matched*(price - avg) - fees           (avg at SALE time;
--         shares -= matched; cost = shares*avg                fees always count;
--         shares = 0 -> cost = 0                              oversell clamps)
--   avg  = cost/shares when shares > 0, else NULL (and a fresh buy re-seeds it).
--
-- Reference implementation + scenario matrix: tracker/positions.py,
-- tests/test_positions_view.py (the integration test asserts SQL == reference).
-- Output columns are IDENTICAL to 0001 — consumers unchanged.

DROP VIEW IF EXISTS current_positions;

CREATE VIEW current_positions AS
WITH RECURSIVE ordered AS (
  SELECT ticker, side, shares, price, fees,
         row_number() OVER (PARTITION BY ticker ORDER BY executed_at, id) AS rn,
         count(*)     OVER (PARTITION BY ticker)                          AS n
  FROM transactions
),
fold AS (
  -- base: first transaction per ticker
  SELECT o.ticker, o.rn, o.n,
         CASE WHEN o.side = 'buy' THEN o.shares ELSE 0 END                    AS shares,
         CASE WHEN o.side = 'buy' THEN o.shares * o.price + o.fees ELSE 0 END AS cost,
         CASE WHEN o.side = 'sell' THEN -o.fees ELSE 0 END                    AS realized
  FROM ordered o
  WHERE o.rn = 1

  UNION ALL

  SELECT o.ticker, o.rn, o.n,
         CASE WHEN o.side = 'buy' THEN f.shares + o.shares
              ELSE f.shares - LEAST(o.shares, f.shares) END,
         CASE WHEN o.side = 'buy' THEN f.cost + o.shares * o.price + o.fees
              WHEN f.shares - LEAST(o.shares, f.shares) > 0
                THEN (f.shares - LEAST(o.shares, f.shares)) * (f.cost / f.shares)
              ELSE 0 END,
         f.realized
           + CASE WHEN o.side = 'sell' THEN
               CASE WHEN f.shares > 0
                    THEN LEAST(o.shares, f.shares) * (o.price - f.cost / f.shares)
                    ELSE 0 END
               - o.fees
             ELSE 0 END
  FROM fold f
  JOIN ordered o ON o.ticker = f.ticker AND o.rn = f.rn + 1
)
SELECT ticker,
       shares,
       CASE WHEN shares > 0 THEN cost / shares END AS avg_cost,
       cost                                        AS invested,
       realized                                    AS realized_pl
FROM fold
WHERE rn = n;

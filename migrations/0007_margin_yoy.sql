-- 0007 — gross margin vs the same quarter last year (percentage points).
-- Seasonality corroboration for the mild margin-compression thesis flag (P4):
-- a mild sequential dip only flags when the margin is ALSO down year-over-year.
ALTER TABLE fundamentals ADD COLUMN IF NOT EXISTS gross_margin_yoy_pp double precision;

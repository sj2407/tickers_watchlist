-- 0003 — allow snapshots.mode = 'intraday' (0001 CHECK only allowed preopen/postclose).
ALTER TABLE snapshots DROP CONSTRAINT IF EXISTS snapshots_mode_check;
ALTER TABLE snapshots ADD CONSTRAINT snapshots_mode_check
  CHECK (mode IN ('preopen', 'intraday', 'postclose'));

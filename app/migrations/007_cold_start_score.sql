-- F2 Cold-Start Score (Whitepaper v4, follow-up "Onboarding Q3 2026")
--
-- Adds four columns to `agents` so we can cache a public-data-derived score
-- for agents that have not yet accumulated behavioral history (i.e. zero
-- endorsements). Cache TTL is 24h (enforced in app/cold_start.py).
--
-- Score sources:
--   * On-chain wallet history (Base L2 via Basescan)  — up to 20 points
--   * GitHub account activity (when available)        — up to 15 points
--   * ERC-8004 registry presence                       — up to 10 points
--
-- A NULL `cold_start_score` with basis = 'no_public_data' means the agent
-- has no externally-derivable score — we deliberately do not invent a value.

ALTER TABLE agents ADD COLUMN IF NOT EXISTS cold_start_score      FLOAT;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS cold_start_basis      VARCHAR(100);
ALTER TABLE agents ADD COLUMN IF NOT EXISTS cold_start_confidence VARCHAR(10);
ALTER TABLE agents ADD COLUMN IF NOT EXISTS cold_start_computed_at TIMESTAMP;

-- Discovery-Tracking-Baseline P2 (SPEC docs/specs/2026-05-21_discovery-tracking-baseline-SPEC.md §3.5 + §4)
--
-- Daily snapshot table for Discovery surfaces:
--   - GSC indexed URLs / impressions / clicks / crawl frequency
--   - nginx bot-hits per User-Agent × endpoint-class
--   - GitHub Stars/Forks/Clones/Views for MoltyCel/* repos
--   - Self-Probe pass/fail (sitemap.xml, llms.txt, /guard/openapi.json, /extendedAgentCard)
--
-- Schema: BIGSERIAL pk + DATE-unique + JSONB payload (schema-flexible for V1
-- iteration without ALTER TABLE migrations).
--
-- Run via P3 cron 00:30 UTC daily (scripts/discovery_snapshot.py — separate PR).
-- Baseline row for 2026-05-21 inserted manually after this migration applies.

CREATE TABLE IF NOT EXISTS discovery_snapshots (
  id           BIGSERIAL PRIMARY KEY,
  snapshot_at  DATE        NOT NULL UNIQUE,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  payload      JSONB       NOT NULL,
  source_run_status TEXT   NOT NULL DEFAULT 'ok'
    CHECK (source_run_status IN ('ok','partial','failed'))
);

CREATE INDEX IF NOT EXISTS idx_discovery_snapshots_at
  ON discovery_snapshots(snapshot_at DESC);

COMMENT ON TABLE discovery_snapshots IS
  'Daily Discovery-Tracking snapshots. One row per day. payload-JSONB shape per SPEC §3.5.';
COMMENT ON COLUMN discovery_snapshots.source_run_status IS
  'ok = all 5 sources captured · partial = some sources failed (see payload.errors) · failed = none captured';

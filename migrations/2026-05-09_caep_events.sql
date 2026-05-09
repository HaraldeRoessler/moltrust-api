-- MolTrust CAEP Profile v1: events table
-- Created 2026-05-09 for Phase 0 Registry-Side endpoints (DSNCON agent-firewall)

CREATE TABLE IF NOT EXISTS caep_events (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT UNIQUE NOT NULL DEFAULT ('evt_' || encode(gen_random_bytes(8), 'hex')),
    did TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN (
        'trust_score_change', 'flag_added', 'flag_removed', 'did_revoked'
    )),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    acknowledged_at TIMESTAMPTZ
);

-- Pending events lookup (most-used query path)
CREATE INDEX IF NOT EXISTS idx_caep_events_did_pending
    ON caep_events (did, created_at)
    WHERE acknowledged_at IS NULL;
-- Note: brief originally had AND expires_at > NOW() in predicate, but NOW() is not IMMUTABLE.
-- Pending lookup query still includes "AND expires_at > NOW()" at query-time.

-- Event_id lookup for ack
CREATE INDEX IF NOT EXISTS idx_caep_events_event_id
    ON caep_events (event_id);

-- Cleanup query (nightly cron)
CREATE INDEX IF NOT EXISTS idx_caep_events_cleanup
    ON caep_events (acknowledged_at)
    WHERE acknowledged_at IS NOT NULL;

COMMENT ON TABLE caep_events IS 'MolTrust CAEP Profile v1 — Continuous Trust Update events';
COMMENT ON COLUMN caep_events.event_id IS 'Public-facing UUID-style identifier (evt_<16hex>)';
COMMENT ON COLUMN caep_events.payload IS 'JSONB, shape depends on event_type';
COMMENT ON COLUMN caep_events.acknowledged_at IS 'NULL = pending; soft-ack, 90d retention before hard-delete';

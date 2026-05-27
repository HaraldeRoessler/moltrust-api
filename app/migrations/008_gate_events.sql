-- F3 Trust-Gating Primitive (Whitepaper v4 follow-up "Flywheel-Zünder")
--
-- Audit log for every `/trust/gate` decision. One row per call. Public
-- endpoint (no API key) so we index by `queried_did` + `created_at` for
-- per-DID rate-investigation, not by caller identity.
--
-- `decision` is constrained to the two values the endpoint returns. Adding
-- a new value (e.g. `REVIEW`) is a future migration.

CREATE TABLE IF NOT EXISTS gate_events (
    id                 SERIAL PRIMARY KEY,
    queried_did        VARCHAR(255) NOT NULL,
    decision           VARCHAR(10)  NOT NULL CHECK (decision IN ('ALLOW', 'DENY')),
    reason             VARCHAR(50),
    score_source       VARCHAR(20),
    trust_score        FLOAT,
    min_score_required FLOAT        NOT NULL,
    allow_cold_start   BOOLEAN      NOT NULL DEFAULT FALSE,
    context            VARCHAR(100),
    caller_ip          VARCHAR(50),
    created_at         TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS gate_events_did_idx        ON gate_events (queried_did);
CREATE INDEX IF NOT EXISTS gate_events_created_at_idx ON gate_events (created_at DESC);

-- Migration runs as `postgres`; the app runs as `moltstack`. Grant the
-- app role full access on the table and its sequence so the endpoint can
-- INSERT audit rows and so test cleanup can DELETE them.
GRANT SELECT, INSERT, UPDATE, DELETE ON gate_events TO moltstack;
GRANT USAGE, SELECT ON SEQUENCE gate_events_id_seq TO moltstack;

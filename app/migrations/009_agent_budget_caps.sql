-- [6] Budget-Cap pro Agent — Operator Dashboard
--
-- Adds a multi-tenancy concept ("operator") on top of the existing
-- self-sovereign `agents.owner_did` model: an agent's owner can claim an
-- operator (themselves or someone else, e.g. an IT department) who then
-- gets to set a monthly CHF cap on the agent's spend.
--
-- Status transitions managed by `app/billing/budget.py`:
--   active     → warning  when spend >= cap * warning_threshold (default 0.8)
--   warning    → capped   when spend >= cap * 1.0
--   capped     → active   automatically at the start of next month
--                         (lazy reset on next spend-event read/write)
--   any        → suspended manually by operator/admin
--
-- Trust-gating intentionally stays oblivious to budget state — Lars-decision
-- 2026-05-27: budget is not trust, separation of concerns.

ALTER TABLE agents ADD COLUMN IF NOT EXISTS operator_did VARCHAR(255);
CREATE INDEX IF NOT EXISTS agents_operator_did_idx ON agents (operator_did);

CREATE TABLE IF NOT EXISTS agent_budget_caps (
    id                   SERIAL PRIMARY KEY,
    operator_did         VARCHAR(255) NOT NULL,
    agent_did            VARCHAR(255) NOT NULL,
    monthly_cap_chf      FLOAT        NOT NULL CHECK (monthly_cap_chf >= 0),
    warning_threshold    FLOAT        NOT NULL DEFAULT 0.8 CHECK (warning_threshold >= 0 AND warning_threshold <= 1),
    current_month_spend  FLOAT        NOT NULL DEFAULT 0.0,
    current_month_key    VARCHAR(7),
    status               VARCHAR(20)  NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'warning', 'capped', 'suspended')),
    created_at           TIMESTAMP    DEFAULT NOW(),
    updated_at           TIMESTAMP    DEFAULT NOW(),
    UNIQUE (operator_did, agent_did)
);
CREATE INDEX IF NOT EXISTS idx_budget_caps_operator ON agent_budget_caps (operator_did);
CREATE INDEX IF NOT EXISTS idx_budget_caps_agent    ON agent_budget_caps (agent_did);

CREATE TABLE IF NOT EXISTS budget_spend_events (
    id              SERIAL PRIMARY KEY,
    operator_did    VARCHAR(255) NOT NULL,
    agent_did       VARCHAR(255) NOT NULL,
    event_type      VARCHAR(50)  NOT NULL,
    amount_chf      FLOAT        NOT NULL CHECK (amount_chf >= 0),
    stripe_price_id VARCHAR(100),
    gate_event_id   INT          REFERENCES gate_events(id) ON DELETE SET NULL,
    created_at      TIMESTAMP    DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_spend_events_operator ON budget_spend_events (operator_did);
CREATE INDEX IF NOT EXISTS idx_spend_events_agent    ON budget_spend_events (agent_did, created_at DESC);

-- Migration runs as `postgres`; app + tests run as `moltstack`. Same pattern
-- as 008_gate_events: GRANT the app role full DML access.
GRANT SELECT, INSERT, UPDATE, DELETE ON agent_budget_caps   TO moltstack;
GRANT SELECT, INSERT, UPDATE, DELETE ON budget_spend_events TO moltstack;
GRANT USAGE, SELECT ON SEQUENCE agent_budget_caps_id_seq    TO moltstack;
GRANT USAGE, SELECT ON SEQUENCE budget_spend_events_id_seq  TO moltstack;

-- FlagRecords: jede Anomalie wird getrackt
CREATE TABLE IF NOT EXISTS flag_records (
    flag_id VARCHAR(100) PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    market_id VARCHAR(200) NOT NULL,
    market_question TEXT,
    market_url TEXT,
    polymarket_slug VARCHAR(200),
    anomaly_type VARCHAR(50),
    anomaly_score INTEGER,
    price_at_flag DECIMAL(10,4),
    volume_24h_usd BIGINT,
    volume_vs_baseline DECIMAL(10,2),
    news_catalyst BOOLEAN DEFAULT FALSE,
    signals JSONB,
    settlement_expected_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'pending',
    created_tweet_id VARCHAR(100)
);

-- OutcomeRecords: nach Settlement
CREATE TABLE IF NOT EXISTS outcome_records (
    flag_id VARCHAR(100) PRIMARY KEY REFERENCES flag_records(flag_id),
    settled_at TIMESTAMPTZ,
    settlement_outcome VARCHAR(10),
    price_at_settlement DECIMAL(10,4),
    price_movement_pct DECIMAL(10,2),
    volume_post_flag_24h BIGINT,
    verdict VARCHAR(20),
    flag_score_contribution DECIMAL(5,2),
    on_chain_anchor VARCHAR(200),
    outcome_tweet_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_flag_records_status ON flag_records(status);
CREATE INDEX IF NOT EXISTS idx_flag_records_market ON flag_records(market_id);

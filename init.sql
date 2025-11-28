-- Local development only: Initialize tables
-- In production (RDS), tables and data already exist - this file is not used

-- Customer consumption metrics
CREATE TABLE IF NOT EXISTS metrics (
    ts TIMESTAMP,
    value NUMERIC,
    customer_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_metrics_customer_id ON metrics(customer_id);
CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(ts);
CREATE INDEX IF NOT EXISTS idx_metrics_customer_ts ON metrics(customer_id, ts);

-- Market prices (EPEX spot prices)
CREATE TABLE IF NOT EXISTS market_prices (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMP NOT NULL,
    price_eur_per_kwh NUMERIC NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_market_prices_ts ON market_prices(ts);


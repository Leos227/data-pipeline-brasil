CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.selic (
    reference_date DATE PRIMARY KEY,
    value NUMERIC(18, 8) NOT NULL,
    series_code INTEGER NOT NULL,
    extracted_at_utc TIMESTAMPTZ NOT NULL,
    loaded_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_payload JSONB NOT NULL
);

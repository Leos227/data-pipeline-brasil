CREATE TABLE IF NOT EXISTS `{project_id}.raw.selic`
(
    reference_date DATE NOT NULL,
    value NUMERIC NOT NULL,
    series_code INT64 NOT NULL,
    extracted_at_utc TIMESTAMP NOT NULL,
    loaded_at_utc TIMESTAMP NOT NULL,
    source_payload STRING NOT NULL
)
PARTITION BY reference_date
CLUSTER BY series_code;

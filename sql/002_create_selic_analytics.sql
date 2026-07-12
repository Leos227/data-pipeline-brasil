CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;


CREATE OR REPLACE VIEW staging.selic_daily AS
SELECT
    reference_date,
    value AS daily_rate,
    series_code,
    extracted_at_utc,
    loaded_at_utc
FROM raw.selic
WHERE
    reference_date IS NOT NULL
    AND value IS NOT NULL;


CREATE OR REPLACE VIEW analytics.selic_daily_metrics AS
SELECT
    reference_date,
    daily_rate,

    LAG(daily_rate) OVER (
        ORDER BY reference_date
    ) AS previous_daily_rate,

    daily_rate - LAG(daily_rate) OVER (
        ORDER BY reference_date
    ) AS daily_change,

    AVG(daily_rate) OVER (
        ORDER BY reference_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS moving_average_7_observations

FROM staging.selic_daily;


CREATE OR REPLACE VIEW analytics.selic_monthly AS
SELECT
    DATE_TRUNC(
        'month',
        reference_date
    )::DATE AS reference_month,

    COUNT(*) AS observation_count,
    ROUND(AVG(daily_rate), 8) AS average_daily_rate,
    MIN(daily_rate) AS minimum_daily_rate,
    MAX(daily_rate) AS maximum_daily_rate,
    MIN(reference_date) AS first_reference_date,
    MAX(reference_date) AS last_reference_date

FROM staging.selic_daily

GROUP BY
    DATE_TRUNC('month', reference_date)

ORDER BY
    reference_month;

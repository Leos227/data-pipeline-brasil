-- 1. Verifica datas duplicadas
SELECT
    reference_date,
    COUNT(*) AS duplicate_count
FROM raw.selic
GROUP BY reference_date
HAVING COUNT(*) > 1;


-- 2. Verifica valores nulos
SELECT *
FROM raw.selic
WHERE
    reference_date IS NULL
    OR value IS NULL
    OR series_code IS NULL;


-- 3. Verifica valores negativos ou zerados
SELECT *
FROM raw.selic
WHERE value <= 0;


-- 4. Compara quantidade entre raw e staging
SELECT
    (SELECT COUNT(*) FROM raw.selic) AS raw_count,
    (SELECT COUNT(*) FROM staging.selic_daily) AS staging_count;


-- 5. Verifica datas futuras
SELECT *
FROM raw.selic
WHERE reference_date > CURRENT_DATE;

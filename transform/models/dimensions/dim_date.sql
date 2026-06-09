{{
  config(materialized='table')
}}

WITH date_spine AS (
    SELECT generate_series(
        (SELECT MIN(scraped_date::date) FROM {{ source('staging', 'stg_lastfm_artists') }}),
        CURRENT_DATE,
        '1 day'::interval
    )::date AS full_date
)

SELECT
    ROW_NUMBER() OVER (ORDER BY full_date)   AS date_id,
    full_date,
    EXTRACT(DAY     FROM full_date)::int     AS day,
    EXTRACT(WEEK    FROM full_date)::int     AS week,
    EXTRACT(MONTH   FROM full_date)::int     AS month,
    EXTRACT(QUARTER FROM full_date)::int     AS quarter,
    EXTRACT(YEAR    FROM full_date)::int     AS year
FROM date_spine

{{
  config(materialized='table')
}}

/*
  Grain: one row per artist per day.

  Source:
    - stg_lastfm_artists  → daily snapshots (merge write disposition)

  Derived measures:
    growth_velocity  = day-over-day % change in lastfm_listeners (LAG window);
                       NULL on the first recorded day for each artist.

    breakout_score   = normalised composite index 0–100, designed to surface
                       fast-growing underground artists:
                         70%  PERCENT_RANK of growth_velocity within the day
                         30%  inverse PERCENT_RANK of listener count within the day
                       Artists with NULL growth_velocity (first day) receive 0.

  spotify_popularity / spotify_followers permanently omitted — removed from the
  Spotify public API in late 2024.
  google_trends_score removed — weekly granularity and mock-only data made it
  non-functional; all rows had is_estimated=TRUE, so LOCF never populated the column.
*/

WITH lastfm_daily AS (
    -- DISTINCT ON deduplicates mock vs real rows for the same artist+date;
    -- keeps the row with the highest listener count (real API data wins over mock).
    SELECT DISTINCT ON (lower(trim(artist_name)), scraped_date::date)
        artist_name,
        scraped_date::date      AS metric_date,
        listeners               AS lastfm_listeners,
        playcount               AS lastfm_playcount
    FROM {{ source('staging', 'stg_lastfm_artists') }}
    WHERE scraped_date IS NOT NULL
    ORDER BY lower(trim(artist_name)), scraped_date::date, listeners DESC
),

with_velocity AS (
    SELECT
        artist_name,
        metric_date,
        lastfm_listeners,
        lastfm_playcount,
        ROUND(
            (lastfm_listeners - LAG(lastfm_listeners) OVER w)::numeric
            / NULLIF(LAG(lastfm_listeners) OVER w, 0) * 100.0
        , 2) AS growth_velocity
    FROM lastfm_daily
    WINDOW w AS (PARTITION BY artist_name ORDER BY metric_date)
),

joined AS (
    SELECT
        a.artist_id,
        d.date_id,
        w.metric_date,
        w.lastfm_listeners,
        w.lastfm_playcount,
        w.growth_velocity
    FROM with_velocity w
    JOIN {{ ref('dim_artist') }} a
        ON lower(trim(w.artist_name)) = lower(trim(a.name))
    JOIN {{ ref('dim_date') }} d
        ON w.metric_date = d.full_date
)

SELECT
    artist_id,
    date_id,
    metric_date,
    lastfm_listeners,
    lastfm_playcount,
    growth_velocity,
    ROUND(
        (
            (
                PERCENT_RANK() OVER (
                    PARTITION BY metric_date
                    ORDER BY GREATEST(COALESCE(growth_velocity, 0), 0)
                ) * 0.7
                + (
                    1.0 - PERCENT_RANK() OVER (
                        PARTITION BY metric_date
                        ORDER BY lastfm_listeners
                    )
                ) * 0.3
            ) * 100.0
        )::numeric
    , 2) AS breakout_score
FROM joined

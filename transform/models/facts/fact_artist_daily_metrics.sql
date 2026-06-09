{{
  config(materialized='table')
}}

/*
  Grain: one row per artist per day.

  Sources:
    - stg_lastfm_artists  → daily snapshots (merge write disposition)
    - stg_google_trends   → weekly scores, forward-filled to daily via correlated subquery

  Derived measures:
    growth_velocity  = day-over-day % change in lastfm_listeners (LAG window)
    breakout_score   = weighted composite: 40% google_trends visibility
                       + 60% positive follower growth momentum

  spotify_popularity / spotify_followers are permanently omitted — removed from
  the Spotify public API in late 2024 and unavailable from any current endpoint.
*/

WITH lastfm_daily AS (
    SELECT
        artist_name,
        scraped_date::date          AS metric_date,
        listeners                   AS lastfm_listeners,
        playcount                   AS lastfm_playcount
    FROM {{ source('staging', 'stg_lastfm_artists') }}
    WHERE scraped_date IS NOT NULL
),

-- Forward-fill Google Trends weekly score to each daily row.
-- Correlated subquery picks the most recent non-estimated weekly score
-- on or before the current metric_date (LOCF — last observation carried forward).
daily_with_trends AS (
    SELECT
        l.artist_name,
        l.metric_date,
        l.lastfm_listeners,
        l.lastfm_playcount,
        (
            SELECT gt.trends_score
            FROM {{ source('staging', 'stg_google_trends') }} gt
            WHERE lower(trim(gt.artist_name)) = lower(trim(l.artist_name))
              AND gt.date::date <= l.metric_date
              AND NOT gt.is_estimated
            ORDER BY gt.date DESC
            LIMIT 1
        ) AS google_trends_score
    FROM lastfm_daily l
),

-- growth_velocity: day-over-day percentage change in unique listeners.
-- NULL on the first recorded day for each artist (no prior value to compare).
with_velocity AS (
    SELECT
        artist_name,
        metric_date,
        lastfm_listeners,
        lastfm_playcount,
        google_trends_score,
        ROUND(
            (lastfm_listeners - LAG(lastfm_listeners) OVER w)::numeric
            / NULLIF(LAG(lastfm_listeners) OVER w, 0) * 100.0
        , 2) AS growth_velocity
    FROM daily_with_trends
    WINDOW w AS (PARTITION BY artist_name ORDER BY metric_date)
)

SELECT
    a.artist_id,
    d.date_id,
    w.metric_date,
    w.lastfm_listeners,
    w.lastfm_playcount,
    w.google_trends_score,
    w.growth_velocity,
    -- breakout_score: 40% search trend visibility + 60% positive growth momentum.
    -- GREATEST(..., 0) treats negative growth as zero contribution (not a breakout signal).
    ROUND(
        COALESCE(w.google_trends_score, 0) * 0.4
        + GREATEST(COALESCE(w.growth_velocity, 0), 0) * 0.6
    , 2) AS breakout_score
FROM with_velocity w
JOIN {{ ref('dim_artist') }} a
    ON lower(trim(w.artist_name)) = lower(trim(a.name))
JOIN {{ ref('dim_date') }} d
    ON w.metric_date = d.full_date

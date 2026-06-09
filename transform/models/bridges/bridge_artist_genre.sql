{{
  config(materialized='table')
}}

-- Maps artists to curated genres (tag_count >= 30 filter mirrors dim_genre).

SELECT
    a.artist_id,
    g.genre_id,
    t.tag_count
FROM {{ source('staging', 'stg_lastfm_artist_tags') }} t
JOIN {{ ref('dim_artist') }} a
    ON lower(trim(t.artist_name)) = lower(trim(a.name))
JOIN {{ ref('dim_genre') }} g
    ON lower(trim(t.tag_name)) = g.genre_name
WHERE t.tag_count >= 30

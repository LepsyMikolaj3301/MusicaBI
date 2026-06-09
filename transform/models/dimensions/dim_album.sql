{{
  config(materialized='table')
}}

-- release_date_precision from Spotify indicates actual precision of the date string:
--   'day'   → "YYYY-MM-DD"   cast directly
--   'month' → "YYYY-MM"      append '-01' before casting
--   'year'  → "YYYY"         append '-01-01' before casting

WITH parsed AS (
    SELECT
        spotify_album_id,
        artist_name,
        title,
        CASE release_date_precision
            WHEN 'day'   THEN release_date::date
            WHEN 'month' THEN (release_date || '-01')::date
            ELSE              (release_date || '-01-01')::date
        END AS release_date,
        album_type
    FROM {{ source('staging', 'stg_spotify_albums') }}
    WHERE spotify_album_id IS NOT NULL
)

SELECT
    ROW_NUMBER() OVER (ORDER BY p.spotify_album_id)  AS album_id,
    p.spotify_album_id,
    p.title,
    p.release_date,
    p.album_type,
    a.artist_id
FROM parsed p
LEFT JOIN {{ ref('dim_artist') }} a
    ON lower(trim(p.artist_name)) = lower(trim(a.name))

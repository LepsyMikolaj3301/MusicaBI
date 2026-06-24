{{
  config(materialized='table')
}}

-- Maps artists to curated genres (tag_count >= 30 filter mirrors dim_genre).
-- Tag names are normalized here to match the normalization applied in dim_genre.

WITH normalized_tags AS (
    SELECT
        artist_name,
        tag_count,
        CASE lower(trim(tag_name))
            WHEN 'kpop'             THEN 'k-pop'
            WHEN 'k pop'            THEN 'k-pop'
            WHEN 'rnb'              THEN 'r&b'
            WHEN 'rhythm and blues' THEN 'r&b'
            WHEN 'hip hop'          THEN 'hip-hop'
            WHEN 'hiphop'           THEN 'hip-hop'
            WHEN 'lo fi'            THEN 'lo-fi'
            WHEN 'lofi'             THEN 'lo-fi'
            WHEN 'post punk'        THEN 'post-punk'
            WHEN 'synth pop'        THEN 'synth-pop'
            WHEN 'synthpop'         THEN 'synth-pop'
            ELSE lower(trim(tag_name))
        END AS genre_name_normalized
    FROM {{ source('staging', 'stg_lastfm_artist_tags') }}
    WHERE tag_count >= 30
      AND tag_name IS NOT NULL
)

SELECT
    a.artist_id,
    g.genre_id,
    t.tag_count
FROM normalized_tags t
JOIN {{ ref('dim_artist') }} a
    ON lower(trim(t.artist_name)) = lower(trim(a.name))
JOIN {{ ref('dim_genre') }} g
    ON t.genre_name_normalized = g.genre_name

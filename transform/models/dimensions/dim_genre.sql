{{
  config(materialized='table')
}}

-- Genres are derived from Last.fm community tags filtered by weight (tag_count >= 30).
-- This threshold removes long-tail noise while keeping established genre labels.

SELECT
    ROW_NUMBER() OVER (ORDER BY normalized)  AS genre_id,
    normalized                               AS genre_name
FROM (
    SELECT DISTINCT
        CASE lower(trim(tag_name))
            WHEN 'kpop'          THEN 'k-pop'
            WHEN 'k pop'         THEN 'k-pop'
            WHEN 'rnb'           THEN 'r&b'
            WHEN 'rhythm and blues' THEN 'r&b'
            WHEN 'hip hop'       THEN 'hip-hop'
            WHEN 'hiphop'        THEN 'hip-hop'
            WHEN 'indie rock'    THEN 'indie rock'
            WHEN 'lo fi'         THEN 'lo-fi'
            WHEN 'lofi'          THEN 'lo-fi'
            WHEN 'post punk'     THEN 'post-punk'
            WHEN 'synth pop'     THEN 'synth-pop'
            WHEN 'synthpop'      THEN 'synth-pop'
            WHEN 'dream pop'     THEN 'dream pop'
            ELSE lower(trim(tag_name))
        END AS normalized
    FROM {{ source('staging', 'stg_lastfm_artist_tags') }}
    WHERE tag_count >= 30
      AND tag_name IS NOT NULL
) distinct_genres

{{
  config(materialized='table')
}}

-- Genres are derived from Last.fm community tags filtered by weight (tag_count >= 30).
-- This threshold removes long-tail noise while keeping established genre labels.

SELECT
    ROW_NUMBER() OVER (ORDER BY lower(trim(tag_name)))  AS genre_id,
    lower(trim(tag_name))                               AS genre_name
FROM (
    SELECT DISTINCT tag_name
    FROM {{ source('staging', 'stg_lastfm_artist_tags') }}
    WHERE tag_count >= 30
      AND tag_name IS NOT NULL
) distinct_genres

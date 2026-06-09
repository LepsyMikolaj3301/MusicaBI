{{
  config(materialized='table')
}}

-- Full folksonomy vocabulary from Last.fm — all tags, no weight filter.
-- Captures niche and emerging artist identifiers beyond canonical genre names.

SELECT
    ROW_NUMBER() OVER (ORDER BY lower(trim(tag_name)))  AS tag_id,
    lower(trim(tag_name))                               AS tag_name
FROM (
    SELECT DISTINCT tag_name
    FROM {{ source('staging', 'stg_lastfm_artist_tags') }}
    WHERE tag_name IS NOT NULL
) distinct_tags

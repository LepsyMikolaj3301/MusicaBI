{{
  config(materialized='table')
}}

-- Maps artists to the full folksonomy tag vocabulary (all tag weights).

SELECT
    a.artist_id,
    ct.tag_id,
    t.tag_count
FROM {{ source('staging', 'stg_lastfm_artist_tags') }} t
JOIN {{ ref('dim_artist') }} a
    ON lower(trim(t.artist_name)) = lower(trim(a.name))
JOIN {{ ref('dim_community_tag') }} ct
    ON lower(trim(t.tag_name)) = ct.tag_name

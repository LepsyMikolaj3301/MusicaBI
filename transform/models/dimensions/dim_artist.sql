{{
  config(materialized='table')
}}

-- Primary source: MusicBrainz (most complete metadata).
-- spotify_id is back-filled from stg_spotify_albums (denormalized per album row).
-- lastfm_id is omitted — Last.fm has no numeric artist identifier.

WITH mb AS (
    SELECT DISTINCT ON (lower(trim(name)))
        mbid,
        name,
        country,
        debut_year
    FROM {{ source('staging', 'stg_musicbrainz_artists') }}
    ORDER BY lower(trim(name)), scraped_at DESC
),

spotify_ids AS (
    SELECT DISTINCT ON (lower(trim(artist_name)))
        spotify_artist_id,
        artist_name
    FROM {{ source('staging', 'stg_spotify_albums') }}
    WHERE spotify_artist_id IS NOT NULL
    ORDER BY lower(trim(artist_name)), scraped_at DESC
)

SELECT
    ROW_NUMBER() OVER (ORDER BY mb.mbid)  AS artist_id,
    mb.name,
    mb.country,
    mb.debut_year,
    mb.mbid                               AS musicbrainz_id,
    sp.spotify_artist_id                  AS spotify_id
FROM mb
LEFT JOIN spotify_ids sp
    ON lower(trim(mb.name)) = lower(trim(sp.artist_name))

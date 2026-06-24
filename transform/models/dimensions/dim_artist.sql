{{
  config(materialized='table')
}}

-- Spine: all monitored artists from Last.fm (100% coverage — autocorrect guarantees a hit).
-- MusicBrainz metadata (country, debut_year, mbid) joined by name where available.
-- spotify_id back-filled from stg_spotify_albums.
-- country is validated to ISO 3166-1 alpha-2; anything else becomes 'Unknown'.

WITH lastfm_spine AS (
    SELECT DISTINCT ON (lower(trim(artist_name)))
        artist_name,
        NULLIF(mbid, '') AS mbid
    FROM {{ source('staging', 'stg_lastfm_artists') }}
    ORDER BY lower(trim(artist_name)), scraped_at DESC
),

mb AS (
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
    ROW_NUMBER() OVER (ORDER BY lower(trim(l.artist_name))) AS artist_id,
    l.artist_name                                           AS name,
    CASE
        WHEN mb.country ~ '^[A-Z]{2}$' THEN mb.country
        ELSE 'Unknown'
    END                                                     AS country,
    mb.debut_year,
    COALESCE(l.mbid, mb.mbid)                              AS musicbrainz_id,
    sp.spotify_artist_id                                    AS spotify_id
FROM lastfm_spine l
LEFT JOIN mb
    ON lower(trim(l.artist_name)) = lower(trim(mb.name))
LEFT JOIN spotify_ids sp
    ON lower(trim(l.artist_name)) = lower(trim(sp.artist_name))

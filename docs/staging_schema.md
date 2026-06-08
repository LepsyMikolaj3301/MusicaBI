# Staging Schema

All tables live in the `staging` schema and are managed by dlt.
Each table includes dlt internals: `_dlt_load_id` and `_dlt_id` (unique constraint).

**Engagement metrics** (listeners, playcount) come from Last.fm — Spotify removed `popularity`, `followers`, and `genres` from their API in late 2024.
**Genre/tag data** comes from `stg_lastfm_artist_tags`.

---

## `stg_lastfm_artists`

Rows: 10 | Write disposition: `merge` on (`artist_name`, `scraped_date`)

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `artist_name` | varchar | NOT NULL | |
| `mbid` | varchar | | MusicBrainz ID (may be empty) |
| `listeners` | bigint | | Unique listener count |
| `playcount` | bigint | | Total scrobbles |
| `url` | varchar | | Last.fm artist URL |
| `scraped_at` | timestamptz | | |
| `scraped_date` | varchar | NOT NULL | Date part of scrape; used as merge key to build time-series |

---

## `stg_lastfm_artist_tags`

Rows: 50 | Write disposition: `replace`

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `artist_name` | varchar | | |
| `tag_name` | varchar | | e.g. `rock`, `alternative` |
| `tag_count` | bigint | | Last.fm tag weight (0–100) |
| `scraped_at` | timestamptz | | |

---

## `stg_musicbrainz_artists`

Rows: 5 | Write disposition: `replace`

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `mbid` | varchar | NOT NULL | Primary key |
| `name` | varchar | | Artist display name |
| `sort_name` | varchar | | e.g. `Swift, Taylor` |
| `country` | varchar | | ISO 3166-1 alpha-2 |
| `disambiguation` | varchar | | Clarifying note (e.g. "UK rock band") |
| `artist_type` | varchar | | `Person`, `Group`, etc. |
| `scraped_at` | timestamptz | | |

---

## `stg_spotify_albums`

Rows: 221 | Write disposition: `replace`

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `spotify_album_id` | varchar | NOT NULL | Primary key |
| `spotify_artist_id` | varchar | | Spotify internal artist ID |
| `artist_name` | varchar | | Denormalized — no separate artists table needed |
| `title` | varchar | | Album title |
| `release_date` | varchar | | Raw string from API (precision varies) |
| `release_date_precision` | varchar | | `day`, `month`, or `year` |
| `album_type` | varchar | | `album`, `single`, or `compilation` |
| `scraped_at` | timestamptz | | |

---

## `stg_google_trends`

Rows: 470 | Write disposition: `replace`

| Column | Type | Nullable | Notes |
| --- | --- | --- | --- |
| `artist_name` | varchar | NOT NULL | |
| `date` | varchar | NOT NULL | Weekly period start date |
| `trends_score` | bigint | | Relative interest (0–100) |
| `is_estimated` | boolean | | Whether score was extrapolated |
| `scraped_at` | timestamptz | | |

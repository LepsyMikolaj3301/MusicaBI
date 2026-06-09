# Dimensional Model — Gap Analysis

Verification of whether current data sources can support the proposed
`Fact_Artist_Daily_Metrics` dimensional model.

---

## Fact_Artist_Daily_Metrics — Measures

| Measure | Status | Source | Notes |
| --- | --- | --- | --- |
| `lastfm_listeners` | ✅ Ready | `stg_lastfm_artists.listeners` | Daily snapshots via merge write disposition; 2 days of history at time of writing, grows with each pipeline run |
| `lastfm_playcount` | ✅ Ready | `stg_lastfm_artists.playcount` | Same as above |
| `google_trends_score` | ⚠️ Granularity mismatch | `stg_google_trends.trends_score` | API returns **weekly** data; fact grain is **daily** — 6 of 7 days per week would be NULL or require forward-fill in the transform layer |
| `growth_velocity` | ⚠️ Computable, data thin | Derived: `Δlisteners / listeners_prev` | Formula is straightforward but only 2 days of history exist — needs several weeks before values are meaningful |
| `breakout_score` | ⚠️ No formula defined | Composite | Presumably combines `growth_velocity` + `google_trends_score`; formula must be defined before implementation |
| `spotify_popularity` | ❌ Permanently unavailable | — | Removed from Spotify Web API in late 2024; no workaround exists |
| `spotify_followers` | ❌ Permanently unavailable | — | Same — removed in the same API change |

---

## Dimensions

### Dim_Artist

| Attribute | Status | Source | Notes |
| --- | --- | --- | --- |
| `name` | ✅ Ready | All sources | |
| `country` | ✅ Ready | `stg_musicbrainz_artists.country` | ISO 3166-1 alpha-2 |
| `musicbrainz_id` | ✅ Ready | `stg_musicbrainz_artists.mbid` | |
| `spotify_id` | ✅ Ready | `stg_spotify_albums.spotify_artist_id` | Denormalized in every album row; needs extraction into Dim_Artist |
| `debut_year` | ✅ Ready | `stg_musicbrainz_artists.debut_year` | Fetched from MusicBrainz `life-span.begin`; NULL when absent |
| `lastfm_id` | ❌ Does not exist | — | Last.fm has no numeric artist ID; it identifies artists by name or `mbid`. This attribute should be dropped from the spec and replaced with `mbid`, which already cross-links Last.fm and MusicBrainz |
| `artist_id` (surrogate) | ⚠️ Must be generated | — | No unified ID exists across sources; must be created in the transform layer (e.g. `ROW_NUMBER()` over a deduplicated artist list from MusicBrainz) |

### Dim_Date

| Status | Notes |
| --- | --- |
| ✅ Fully generatable | Standard calendar table — `date_id`, `day`, `week`, `month`, `quarter`, `year`. No API needed; generated once in the transform layer from a date range. |

### Dim_Album

| Attribute | Status | Notes |
| --- | --- | --- |
| `spotify_album_id` | ✅ Ready | `stg_spotify_albums.spotify_album_id` |
| `title` | ✅ Ready | `stg_spotify_albums.title` |
| `album_type` | ✅ Ready | Values present: `album`, `single`; `compilation` not seen for current artists |
| `release_date` | ⚠️ Needs parsing | Raw string with mixed precision — some older releases have year-only values (e.g. `1995`). Transform layer must handle all three precision levels: `day`, `month`, `year` |
| `artist_id` | ⚠️ Must be joined | Resolved via `artist_name` once surrogate keys exist in Dim_Artist |

### Dim_Genre (Snowflake optional)

| Status | Notes |
| --- | --- |
| ⚠️ No clean source | Spotify genres are gone. Last.fm tags are community-sourced and noisy (`sad`, `seen live`, `90s` are not genres). If Dim_Genre is meant to be a curated taxonomy, it requires either manual curation or a filter (e.g. `tag_count > 50` plus a blocklist of non-genre tags). |

### Dim_Community_Tag (Snowflake optional)

| Status | Notes |
| --- | --- |
| ✅ Ready | `stg_lastfm_artist_tags` — `tag_name` + generated surrogate key. Direct source. |

---

## Summary of Required Actions

### Retire from model spec — fields that cannot be sourced

- `spotify_popularity` — permanently removed from Spotify API
- `spotify_followers` — permanently removed from Spotify API
- `lastfm_id` — concept does not exist in Last.fm; replace with `mbid` throughout

### Google Trends granularity — pick one approach

- **Option A:** Accept NULLs for non-week-start days, aggregate at weekly level in reports
- **Option B:** Forward-fill the weekly score across all 7 days of the week in the transform layer

### Define `breakout_score` formula

Data availability is not the blocker — the formula itself must be agreed on before building.
A common baseline: weighted composite of normalised `growth_velocity` and `google_trends_score`.

### Generate surrogate keys in transform layer

`artist_id` in Dim_Artist must be a generated surrogate; no single source provides a unified ID.
Resolution order: MusicBrainz `mbid` → Last.fm `mbid` → Spotify `spotify_artist_id`.

---

## Overall Readiness

| Area | Readiness |
| --- | --- |
| Core engagement metrics (listeners, playcount) | ✅ |
| Time dimension | ✅ |
| Album dimension | ✅ (minor parsing work) |
| Community tags | ✅ |
| Artist dimension | ⚠️ — surrogate key needed (transform layer) |
| Trends metric | ⚠️ — granularity mismatch to resolve |
| Derived metrics (velocity, breakout) | ⚠️ — formula definition needed |
| Spotify engagement metrics | ❌ — permanently unavailable |
| Clean genre taxonomy | ❌ — no reliable source; Last.fm tags are a noisy proxy |

from typing import Iterator
from datetime import datetime, timezone

import dlt
from dlt.sources.helpers import requests

LASTFM_API_URL = "http://ws.audioscrobbler.com/2.0/"


# ---------------------------------------------------------------------------
# Private helpers (pure data-fetching, no dlt machinery — easy to unit-test)
# ---------------------------------------------------------------------------

def _fetch_artist_info(api_key: str, artist_name: str) -> dict | None:
    response = requests.get(
        LASTFM_API_URL,
        params={
            "method": "artist.getInfo",
            "artist": artist_name,
            "autocorrect": 1,
            "api_key": api_key,
            "format": "json",
        },
    )
    response.raise_for_status()
    data = response.json()
    artist = data.get("artist", {})
    if not artist.get("name"):
        return None
    stats = artist.get("stats", {})
    return {
        "artist_name": artist.get("name", artist_name),
        "mbid": artist.get("mbid") or "",
        "listeners": int(stats.get("listeners") or 0),
        "playcount": int(stats.get("playcount") or 0),
        "url": artist.get("url", ""),
    }


def _fetch_artist_top_tags(api_key: str, artist_name: str) -> list[dict]:
    response = requests.get(
        LASTFM_API_URL,
        params={
            "method": "artist.getTopTags",
            "artist": artist_name,
            "autocorrect": 1,
            "api_key": api_key,
            "format": "json",
        },
    )
    response.raise_for_status()
    data = response.json()
    tags = data.get("toptags", {}).get("tag", [])
    return [
        {
            "artist_name": artist_name,
            "tag_name": tag.get("name", ""),
            "tag_count": int(tag.get("count") or 0),
        }
        for tag in tags[:10]  # top-10 tags per artist
    ]


# ---------------------------------------------------------------------------
# dlt source + resources
# ---------------------------------------------------------------------------

@dlt.source(name="lastfm")
def lastfm_source(
    api_key: str = dlt.secrets.value,
    page_limit: int = dlt.config.value,
    items_per_page: int = dlt.config.value,
    artist_names: list | None = None,
):
    return (
        lastfm_artists_info(api_key, artist_names or []),
        lastfm_artist_tags(api_key, artist_names or []),
    )


# --- artist-specific resources ---

@dlt.resource(
    name="stg_lastfm_artists",
    # merge so running twice on the same day doesn't duplicate rows;
    # append across days builds the time-series needed for lag calculation
    write_disposition="merge",
    primary_key=["artist_name", "scraped_date"],
)
def lastfm_artists_info(api_key: str, artist_names: list) -> Iterator[dict]:
    scraped_at = datetime.now(timezone.utc).isoformat()
    scraped_date = datetime.now(timezone.utc).date().isoformat()
    for name in artist_names:
        data = _fetch_artist_info(api_key, name)
        if data:
            yield {**data, "scraped_at": scraped_at, "scraped_date": scraped_date}


@dlt.resource(
    name="stg_lastfm_artist_tags",
    write_disposition="replace",
)
def lastfm_artist_tags(api_key: str, artist_names: list) -> Iterator[dict]:
    scraped_at = datetime.now(timezone.utc).isoformat()
    for name in artist_names:
        for tag in _fetch_artist_top_tags(api_key, name):
            yield {**tag, "scraped_at": scraped_at}

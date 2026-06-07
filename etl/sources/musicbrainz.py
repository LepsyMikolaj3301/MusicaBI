import time
from typing import Iterator
from datetime import datetime, timezone

import dlt
import requests

MUSICBRAINZ_API_BASE = "https://musicbrainz.org/ws/2"
# MusicBrainz requires <= 1 req/sec without auth; 1.1 s gives a small margin
_RATE_LIMIT_SEC = 1.1
# Required by MusicBrainz API policy
_USER_AGENT = "MusicaBI/0.1 (mikolaj.lepsy@gmail.com)"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fetch_musicbrainz_artist(artist_name: str) -> dict | None:
    resp = requests.get(
        f"{MUSICBRAINZ_API_BASE}/artist/",
        params={"query": f'artist:"{artist_name}"', "fmt": "json", "limit": 1},
        headers={"User-Agent": _USER_AGENT},
        timeout=15,
    )
    resp.raise_for_status()
    artists = resp.json().get("artists", [])
    if not artists:
        return None
    a = artists[0]
    area = a.get("area") or {}
    return {
        "mbid": a.get("id", ""),
        "name": a.get("name", artist_name),
        "sort_name": a.get("sort-name", ""),
        # country ISO code if present, else area name, else "Unknown"
        "country": a.get("country") or area.get("name") or "Unknown",
        "disambiguation": a.get("disambiguation", ""),
        "artist_type": a.get("type", ""),
    }


# ---------------------------------------------------------------------------
# dlt source + resources
# ---------------------------------------------------------------------------

@dlt.source(name="musicbrainz")
def musicbrainz_source(artist_names: list | None = None):
    return (musicbrainz_artists(artist_names or []),)


@dlt.resource(
    name="stg_musicbrainz_artists",
    write_disposition="replace",
    primary_key="mbid",
)
def musicbrainz_artists(artist_names: list) -> Iterator[dict]:
    scraped_at = datetime.now(timezone.utc).isoformat()
    for name in artist_names:
        data = _fetch_musicbrainz_artist(name)
        time.sleep(_RATE_LIMIT_SEC)
        if data:
            yield {**data, "scraped_at": scraped_at}

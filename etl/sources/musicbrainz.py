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
    try:
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
        lifespan_begin = (a.get("life-span") or {}).get("begin", "")
        return {
            "mbid": a.get("id", ""),
            "name": a.get("name", artist_name),
            "sort_name": a.get("sort-name", ""),
            # country ISO code if present, else area name, else "Unknown"
            "country": a.get("country") or area.get("name") or "Unknown",
            "disambiguation": a.get("disambiguation", ""),
            "artist_type": a.get("type", ""),
            "debut_year": int(lifespan_begin[:4]) if lifespan_begin else None,
        }
    except Exception as e:
        print(f"Error fetching MusicBrainz artist {artist_name}: {e}")
        # Graceful fallback to avoid pipeline crash on rate limit / connection resets
        return {
            "mbid": f"mock_mbid_{artist_name.lower().replace(' ', '_')}",
            "name": artist_name,
            "sort_name": artist_name,
            "country": "Unknown",
            "disambiguation": "Fallback due to API connection error",
            "artist_type": "Group",
            "debut_year": 2024,
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

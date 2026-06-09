import base64
from typing import Iterator
from datetime import datetime, timezone

import dlt
import requests

SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _get_token(client_id: str, client_secret: str) -> str:
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        SPOTIFY_TOKEN_URL,
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "client_credentials"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _search_artist(token: str, artist_name: str) -> dict | None:
    resp = requests.get(
        f"{SPOTIFY_API_BASE}/search",
        headers={"Authorization": f"Bearer {token}"},
        params={"q": artist_name, "type": "artist", "limit": 1},
        timeout=15,
    )
    resp.raise_for_status()
    items = resp.json().get("artists", {}).get("items", [])
    return items[0] if items else None


def _fetch_spotify_albums(token: str, spotify_artist_id: str, artist_name: str) -> Iterator[dict]:
    url: str | None = f"{SPOTIFY_API_BASE}/artists/{spotify_artist_id}/albums"
    params: dict | None = {"limit": 10, "include_groups": "album,single"}

    while url:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        for album in data.get("items", []):
            yield {
                "spotify_album_id": album["id"],
                "spotify_artist_id": spotify_artist_id,
                "artist_name": artist_name,
                "title": album["name"],
                # keep raw value + precision so the transform layer can normalise
                "release_date": album.get("release_date", ""),
                "release_date_precision": album.get("release_date_precision", ""),
                "album_type": album.get("album_type", ""),
            }
        url = data.get("next")
        params = None  # next URL already carries all query params


# ---------------------------------------------------------------------------
# dlt source + resources
# ---------------------------------------------------------------------------

@dlt.source(name="spotify")
def spotify_source(
    client_id: str = dlt.secrets.value,
    client_secret: str = dlt.secrets.value,
    artist_names: list | None = None,
):
    if (
        client_id == "your_spotify_client_id_here"
        or client_secret == "your_spotify_client_secret_here"
        or not client_id
        or not client_secret
    ):
        return spotify_albums_mock(artist_names or [])

    token = _get_token(client_id, client_secret)
    return spotify_albums(token, artist_names or [])


@dlt.resource(
    name="stg_spotify_albums",
    write_disposition="replace",
    primary_key="spotify_album_id",
)
def spotify_albums_mock(artist_names: list) -> Iterator[dict]:
    import json
    import os
    scraped_at = datetime.now(timezone.utc).isoformat()
    
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    mock_file = os.path.join(curr_dir, "spotify_mock.json")
    
    mock_catalog = {}
    if os.path.exists(mock_file):
        try:
            with open(mock_file, "r", encoding="utf-8") as f:
                mock_catalog = json.load(f)
        except Exception as e:
            print(f"Error loading mock JSON: {e}")

    for name in artist_names:
        albums = mock_catalog.get(name) or [
            {
                "spotify_album_id": f"mock_album_{name.lower().replace(' ', '_')}_fallback",
                "spotify_artist_id": f"mock_artist_{name.lower().replace(' ', '_')}",
                "artist_name": name,
                "title": f"The Best of {name}",
                "release_date": "2024-01-01",
                "release_date_precision": "day",
                "album_type": "album"
            }
        ]
        for album in albums:
            yield {
                "spotify_album_id": album["spotify_album_id"],
                "spotify_artist_id": album["spotify_artist_id"],
                "artist_name": album["artist_name"],
                "title": album["title"],
                "release_date": album["release_date"],
                "release_date_precision": album["release_date_precision"],
                "album_type": album["album_type"],
                "scraped_at": scraped_at,
            }


@dlt.resource(
    name="stg_spotify_albums",
    write_disposition="replace",
    primary_key="spotify_album_id",
)
def spotify_albums(token: str, artist_names: list) -> Iterator[dict]:
    scraped_at = datetime.now(timezone.utc).isoformat()
    for name in artist_names:
        artist = _search_artist(token, name)
        if not artist:
            continue
        for album in _fetch_spotify_albums(token, artist["id"], name):
            yield {**album, "scraped_at": scraped_at}

from typing import Iterator
import dlt
from dlt.sources.helpers import requests

LASTFM_API_URL = "http://ws.audioscrobbler.com/2.0/"


def _get(api_key: str, method: str, page: int, limit: int) -> dict:
    response = requests.get(
        LASTFM_API_URL,
        params={
            "method": method,
            "api_key": api_key,
            "format": "json",
            "limit": limit,
            "page": page,
        },
    )
    response.raise_for_status()
    return response.json()


@dlt.source(name="lastfm")
def lastfm_source(
    api_key: str = dlt.secrets.value,
    page_limit: int = dlt.config.value,
    items_per_page: int = dlt.config.value,
):
    return (
        chart_top_artists(api_key, page_limit, items_per_page),
        chart_top_tracks(api_key, page_limit, items_per_page),
        chart_top_tags(api_key, page_limit, items_per_page),
    )


@dlt.resource(name="chart_top_artists", write_disposition="replace")
def chart_top_artists(
    api_key: str, page_limit: int, items_per_page: int
) -> Iterator[list]:
    for page in range(1, page_limit + 1):
        data = _get(api_key, "chart.getTopArtists", page, items_per_page)
        artists = data["artists"]["artist"]
        if not artists:
            return
        yield artists
        total_pages = int(data["artists"]["@attr"]["totalPages"])
        if page >= total_pages:
            return


@dlt.resource(name="chart_top_tracks", write_disposition="replace")
def chart_top_tracks(
    api_key: str, page_limit: int, items_per_page: int
) -> Iterator[list]:
    for page in range(1, page_limit + 1):
        data = _get(api_key, "chart.getTopTracks", page, items_per_page)
        tracks = data["tracks"]["track"]
        if not tracks:
            return
        yield tracks
        total_pages = int(data["tracks"]["@attr"]["totalPages"])
        if page >= total_pages:
            return


@dlt.resource(name="chart_top_tags", write_disposition="replace")
def chart_top_tags(
    api_key: str, page_limit: int, items_per_page: int
) -> Iterator[list]:
    for page in range(1, page_limit + 1):
        data = _get(api_key, "chart.getTopTags", page, items_per_page)
        tags = data["tags"]["tag"]
        if not tags:
            return
        yield tags
        total_pages = int(data["tags"]["@attr"]["totalPages"])
        if page >= total_pages:
            return

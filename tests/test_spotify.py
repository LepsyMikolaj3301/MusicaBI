"""
Tests for etl/sources/spotify.py
"""
from unittest.mock import patch, MagicMock, call

import pytest

from etl.sources.spotify import (
    _get_token,
    _search_artist,
    _fetch_spotify_artist,
    _fetch_spotify_albums,
)


# ---------------------------------------------------------------------------
# Sample payloads
# ---------------------------------------------------------------------------

TOKEN_RESPONSE = {"access_token": "test_token_abc", "token_type": "Bearer"}

SEARCH_RESPONSE_HIT = {
    "artists": {
        "items": [
            {
                "id": "4Z8W4fkeB5StMa5nKAIVGB",
                "name": "Radiohead",
                "popularity": 79,
                "followers": {"total": 5_200_000},
                "genres": ["alternative rock", "art rock", "oxford indie"],
            }
        ]
    }
}

SEARCH_RESPONSE_MISS = {"artists": {"items": []}}

ALBUMS_PAGE_1 = {
    "items": [
        {
            "id": "album_001",
            "name": "OK Computer",
            "release_date": "1997-05-28",
            "release_date_precision": "day",
            "album_type": "album",
        },
        {
            "id": "album_002",
            "name": "Kid A",
            "release_date": "2000-10-02",
            "release_date_precision": "day",
            "album_type": "album",
        },
    ],
    "next": "https://api.spotify.com/v1/artists/.../albums?offset=50",
}

ALBUMS_PAGE_2 = {
    "items": [
        {
            "id": "album_003",
            "name": "Amnesiac",
            "release_date": "2001-06-05",
            "release_date_precision": "day",
            "album_type": "album",
        }
    ],
    "next": None,
}


def _mock(json_data):
    m = MagicMock()
    m.json.return_value = json_data
    m.raise_for_status = MagicMock()
    return m


# ---------------------------------------------------------------------------
# _get_token
# ---------------------------------------------------------------------------

class TestGetToken:
    @patch("etl.sources.spotify.requests.post")
    def test_returns_access_token_string(self, mock_post):
        mock_post.return_value = _mock(TOKEN_RESPONSE)
        token = _get_token("client_id", "client_secret")
        assert token == "test_token_abc"

    @patch("etl.sources.spotify.requests.post")
    def test_uses_client_credentials_grant(self, mock_post):
        mock_post.return_value = _mock(TOKEN_RESPONSE)
        _get_token("cid", "csec")
        _, kwargs = mock_post.call_args
        assert kwargs["data"]["grant_type"] == "client_credentials"

    @patch("etl.sources.spotify.requests.post")
    def test_authorization_header_is_basic(self, mock_post):
        mock_post.return_value = _mock(TOKEN_RESPONSE)
        _get_token("cid", "csec")
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"].startswith("Basic ")


# ---------------------------------------------------------------------------
# _search_artist
# ---------------------------------------------------------------------------

class TestSearchArtist:
    @patch("etl.sources.spotify.requests.get")
    def test_returns_first_result(self, mock_get):
        mock_get.return_value = _mock(SEARCH_RESPONSE_HIT)
        result = _search_artist("token", "Radiohead")
        assert result is not None
        assert result["id"] == "4Z8W4fkeB5StMa5nKAIVGB"
        assert result["name"] == "Radiohead"

    @patch("etl.sources.spotify.requests.get")
    def test_returns_none_when_no_results(self, mock_get):
        mock_get.return_value = _mock(SEARCH_RESPONSE_MISS)
        result = _search_artist("token", "xyzunknownband")
        assert result is None


# ---------------------------------------------------------------------------
# _fetch_spotify_artist
# ---------------------------------------------------------------------------

class TestFetchSpotifyArtist:
    @patch("etl.sources.spotify.requests.get")
    def test_schema_and_types(self, mock_get):
        mock_get.return_value = _mock(SEARCH_RESPONSE_HIT)
        result = _fetch_spotify_artist("token", "Radiohead")

        assert result is not None
        assert set(result.keys()) == {
            "spotify_id", "name", "popularity", "followers_total", "genres"
        }
        assert isinstance(result["popularity"], int)
        assert isinstance(result["followers_total"], int)
        assert isinstance(result["genres"], list)

    @patch("etl.sources.spotify.requests.get")
    def test_returns_none_for_unknown_artist(self, mock_get):
        mock_get.return_value = _mock(SEARCH_RESPONSE_MISS)
        result = _fetch_spotify_artist("token", "NoSuchBand")
        assert result is None

    @patch("etl.sources.spotify.requests.get")
    def test_genres_is_list_even_when_empty(self, mock_get):
        no_genres = {
            "artists": {
                "items": [{"id": "x", "name": "New Artist", "popularity": 5,
                           "followers": {"total": 100}, "genres": []}]
            }
        }
        mock_get.return_value = _mock(no_genres)
        result = _fetch_spotify_artist("token", "New Artist")
        assert result["genres"] == []


# ---------------------------------------------------------------------------
# _fetch_spotify_albums
# ---------------------------------------------------------------------------

class TestFetchSpotifyAlbums:
    @patch("etl.sources.spotify.requests.get")
    def test_yields_albums_across_pages(self, mock_get):
        mock_get.side_effect = [_mock(ALBUMS_PAGE_1), _mock(ALBUMS_PAGE_2)]
        albums = list(_fetch_spotify_albums("token", "artist_id_001", "Radiohead"))

        assert len(albums) == 3

    @patch("etl.sources.spotify.requests.get")
    def test_album_schema(self, mock_get):
        mock_get.side_effect = [_mock(ALBUMS_PAGE_1), _mock(ALBUMS_PAGE_2)]
        albums = list(_fetch_spotify_albums("token", "artist_id_001", "Radiohead"))

        for album in albums:
            assert "spotify_album_id" in album
            assert "spotify_artist_id" in album
            assert "artist_name" in album
            assert "title" in album
            assert "release_date" in album
            assert "release_date_precision" in album
            assert "album_type" in album

    @patch("etl.sources.spotify.requests.get")
    def test_artist_id_and_name_propagated(self, mock_get):
        mock_get.side_effect = [_mock(ALBUMS_PAGE_1), _mock(ALBUMS_PAGE_2)]
        albums = list(_fetch_spotify_albums("token", "artist_id_001", "Radiohead"))

        assert all(a["spotify_artist_id"] == "artist_id_001" for a in albums)
        assert all(a["artist_name"] == "Radiohead" for a in albums)

    @patch("etl.sources.spotify.requests.get")
    def test_release_date_kept_as_raw_string(self, mock_get):
        # raw value intentionally preserved — normalisation happens in transform
        mock_get.side_effect = [_mock(ALBUMS_PAGE_1), _mock(ALBUMS_PAGE_2)]
        albums = list(_fetch_spotify_albums("token", "artist_id_001", "Radiohead"))

        assert albums[0]["release_date"] == "1997-05-28"
        assert albums[0]["release_date_precision"] == "day"

    @patch("etl.sources.spotify.requests.get")
    def test_pagination_stops_when_next_is_none(self, mock_get):
        single_page = {**ALBUMS_PAGE_1, "next": None}
        mock_get.return_value = _mock(single_page)
        albums = list(_fetch_spotify_albums("token", "aid", "Artist"))

        assert mock_get.call_count == 1
        assert len(albums) == 2

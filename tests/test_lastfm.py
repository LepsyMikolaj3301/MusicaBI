"""
Tests for etl/sources/lastfm.py

Focus: schema correctness, type coercion, and edge-case handling of the
private fetch helpers. dlt-decorated resources are not invoked directly so
we stay free of dlt pipeline machinery in unit tests.
"""
from unittest.mock import patch, MagicMock

import pytest

from etl.sources.lastfm import _fetch_artist_info, _fetch_artist_top_tags


# ---------------------------------------------------------------------------
# Fixtures / sample payloads
# ---------------------------------------------------------------------------

ARTIST_INFO_FULL = {
    "artist": {
        "name": "Radiohead",
        "mbid": "a74b1b7f-71a5-4011-9441-d0b5e4122711",
        "stats": {"listeners": "4218443", "playcount": "123456789"},
        "url": "https://www.last.fm/music/Radiohead",
    }
}

ARTIST_INFO_NO_MBID = {
    "artist": {
        "name": "Niche Artist",
        "mbid": "",
        "stats": {"listeners": "500", "playcount": "1000"},
        "url": "",
    }
}

ARTIST_INFO_MISSING_STATS = {
    "artist": {
        "name": "Empty Stats Artist",
        "mbid": "",
        "stats": {},
        "url": "",
    }
}

ARTIST_INFO_EMPTY = {"artist": {}}

TOP_TAGS_FULL = {
    "toptags": {
        "tag": [
            {"name": "alternative rock", "count": "100"},
            {"name": "art rock", "count": "90"},
            {"name": "post-rock", "count": "80"},
        ]
    }
}

TOP_TAGS_EMPTY = {"toptags": {"tag": []}}

TOP_TAGS_MANY = {
    "toptags": {
        "tag": [{"name": f"tag_{i}", "count": str(100 - i)} for i in range(20)]
    }
}


def _mock_get(json_data):
    m = MagicMock()
    m.json.return_value = json_data
    m.raise_for_status = MagicMock()
    return m


# ---------------------------------------------------------------------------
# _fetch_artist_info
# ---------------------------------------------------------------------------

class TestFetchArtistInfo:
    @patch("etl.sources.lastfm.requests.get")
    def test_returns_all_expected_keys(self, mock_get):
        mock_get.return_value = _mock_get(ARTIST_INFO_FULL)
        result = _fetch_artist_info("key", "Radiohead")

        assert result is not None
        assert set(result.keys()) == {"artist_name", "mbid", "listeners", "playcount", "url"}

    @patch("etl.sources.lastfm.requests.get")
    def test_listeners_and_playcount_are_integers(self, mock_get):
        mock_get.return_value = _mock_get(ARTIST_INFO_FULL)
        result = _fetch_artist_info("key", "Radiohead")

        assert isinstance(result["listeners"], int)
        assert isinstance(result["playcount"], int)
        assert result["listeners"] == 4_218_443
        assert result["playcount"] == 123_456_789

    @patch("etl.sources.lastfm.requests.get")
    def test_artist_name_comes_from_api(self, mock_get):
        # API can autocorrect the name (e.g. "radiohead" → "Radiohead")
        mock_get.return_value = _mock_get(ARTIST_INFO_FULL)
        result = _fetch_artist_info("key", "radiohead")

        assert result["artist_name"] == "Radiohead"

    @patch("etl.sources.lastfm.requests.get")
    def test_missing_mbid_returns_empty_string(self, mock_get):
        mock_get.return_value = _mock_get(ARTIST_INFO_NO_MBID)
        result = _fetch_artist_info("key", "Niche Artist")

        assert result is not None
        assert result["mbid"] == ""

    @patch("etl.sources.lastfm.requests.get")
    def test_missing_stats_defaults_to_zero(self, mock_get):
        mock_get.return_value = _mock_get(ARTIST_INFO_MISSING_STATS)
        result = _fetch_artist_info("key", "Empty Stats Artist")

        assert result is not None
        assert result["listeners"] == 0
        assert result["playcount"] == 0

    @patch("etl.sources.lastfm.requests.get")
    def test_empty_artist_object_returns_none(self, mock_get):
        mock_get.return_value = _mock_get(ARTIST_INFO_EMPTY)
        result = _fetch_artist_info("key", "Ghost")

        assert result is None

    @patch("etl.sources.lastfm.requests.get")
    def test_passes_correct_api_params(self, mock_get):
        mock_get.return_value = _mock_get(ARTIST_INFO_FULL)
        _fetch_artist_info("MY_KEY", "Radiohead")

        call_params = mock_get.call_args.kwargs.get("params") or mock_get.call_args.args[1]
        assert call_params["method"] == "artist.getInfo"
        assert call_params["artist"] == "Radiohead"
        assert call_params["api_key"] == "MY_KEY"


# ---------------------------------------------------------------------------
# _fetch_artist_top_tags
# ---------------------------------------------------------------------------

class TestFetchArtistTopTags:
    @patch("etl.sources.lastfm.requests.get")
    def test_returns_list_of_dicts_with_correct_keys(self, mock_get):
        mock_get.return_value = _mock_get(TOP_TAGS_FULL)
        results = _fetch_artist_top_tags("key", "Radiohead")

        assert isinstance(results, list)
        assert len(results) == 3
        for r in results:
            assert set(r.keys()) == {"artist_name", "tag_name", "tag_count"}

    @patch("etl.sources.lastfm.requests.get")
    def test_tag_count_is_integer(self, mock_get):
        mock_get.return_value = _mock_get(TOP_TAGS_FULL)
        results = _fetch_artist_top_tags("key", "Radiohead")

        for r in results:
            assert isinstance(r["tag_count"], int)

    @patch("etl.sources.lastfm.requests.get")
    def test_artist_name_propagated_to_every_row(self, mock_get):
        mock_get.return_value = _mock_get(TOP_TAGS_FULL)
        results = _fetch_artist_top_tags("key", "Radiohead")

        assert all(r["artist_name"] == "Radiohead" for r in results)

    @patch("etl.sources.lastfm.requests.get")
    def test_capped_at_ten_tags(self, mock_get):
        mock_get.return_value = _mock_get(TOP_TAGS_MANY)
        results = _fetch_artist_top_tags("key", "BigArtist")

        assert len(results) == 10

    @patch("etl.sources.lastfm.requests.get")
    def test_empty_tags_returns_empty_list(self, mock_get):
        mock_get.return_value = _mock_get(TOP_TAGS_EMPTY)
        results = _fetch_artist_top_tags("key", "NewArtist")

        assert results == []

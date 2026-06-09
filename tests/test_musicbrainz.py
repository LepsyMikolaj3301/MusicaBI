"""
Tests for etl/sources/musicbrainz.py
"""
from unittest.mock import patch, MagicMock

import pytest

from etl.sources.musicbrainz import _fetch_musicbrainz_artist


# ---------------------------------------------------------------------------
# Sample payloads
# ---------------------------------------------------------------------------

MB_RESPONSE_FULL = {
    "artists": [
        {
            "id": "a74b1b7f-71a5-4011-9441-d0b5e4122711",
            "name": "Radiohead",
            "sort-name": "Radiohead",
            "country": "GB",
            "area": {"name": "United Kingdom"},
            "disambiguation": "",
            "type": "Group",
            "life-span": {"begin": "1985-01-01", "ended": False},
        }
    ]
}

MB_RESPONSE_NO_COUNTRY = {
    "artists": [
        {
            "id": "some-uuid",
            "name": "Mystery Artist",
            "sort-name": "Mystery Artist",
            # no "country" key at all
            "area": {"name": "Worldwide"},
            "disambiguation": "",
            "type": "Person",
        }
    ]
}

MB_RESPONSE_NO_AREA_EITHER = {
    "artists": [
        {
            "id": "some-uuid-2",
            "name": "Anonymous",
            "sort-name": "Anonymous",
            "disambiguation": "",
            "type": "Person",
        }
    ]
}

MB_RESPONSE_EMPTY = {"artists": []}


def _mock(json_data):
    m = MagicMock()
    m.json.return_value = json_data
    m.raise_for_status = MagicMock()
    return m


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFetchMusicBrainzArtist:
    @patch("etl.sources.musicbrainz.requests.get")
    def test_schema_and_types(self, mock_get):
        mock_get.return_value = _mock(MB_RESPONSE_FULL)
        result = _fetch_musicbrainz_artist("Radiohead")

        assert result is not None
        assert set(result.keys()) == {
            "mbid", "name", "sort_name", "country", "disambiguation", "artist_type", "debut_year"
        }

    @patch("etl.sources.musicbrainz.requests.get")
    def test_mbid_is_string(self, mock_get):
        mock_get.return_value = _mock(MB_RESPONSE_FULL)
        result = _fetch_musicbrainz_artist("Radiohead")

        assert isinstance(result["mbid"], str)
        assert result["mbid"] == "a74b1b7f-71a5-4011-9441-d0b5e4122711"

    @patch("etl.sources.musicbrainz.requests.get")
    def test_country_from_iso_code(self, mock_get):
        mock_get.return_value = _mock(MB_RESPONSE_FULL)
        result = _fetch_musicbrainz_artist("Radiohead")

        assert result["country"] == "GB"

    @patch("etl.sources.musicbrainz.requests.get")
    def test_country_falls_back_to_area_name(self, mock_get):
        mock_get.return_value = _mock(MB_RESPONSE_NO_COUNTRY)
        result = _fetch_musicbrainz_artist("Mystery Artist")

        assert result["country"] == "Worldwide"

    @patch("etl.sources.musicbrainz.requests.get")
    def test_country_defaults_to_unknown_when_both_missing(self, mock_get):
        mock_get.return_value = _mock(MB_RESPONSE_NO_AREA_EITHER)
        result = _fetch_musicbrainz_artist("Anonymous")

        assert result["country"] == "Unknown"

    @patch("etl.sources.musicbrainz.requests.get")
    def test_empty_result_returns_none(self, mock_get):
        mock_get.return_value = _mock(MB_RESPONSE_EMPTY)
        result = _fetch_musicbrainz_artist("NoSuchArtist")

        assert result is None

    @patch("etl.sources.musicbrainz.requests.get")
    def test_user_agent_header_is_set(self, mock_get):
        mock_get.return_value = _mock(MB_RESPONSE_FULL)
        _fetch_musicbrainz_artist("Radiohead")

        _, kwargs = mock_get.call_args
        assert "User-Agent" in kwargs["headers"]
        assert "MusicaBI" in kwargs["headers"]["User-Agent"]

    @patch("etl.sources.musicbrainz.requests.get")
    def test_debut_year_extracted_as_integer(self, mock_get):
        mock_get.return_value = _mock(MB_RESPONSE_FULL)
        result = _fetch_musicbrainz_artist("Radiohead")

        assert result["debut_year"] == 1985
        assert isinstance(result["debut_year"], int)

    @patch("etl.sources.musicbrainz.requests.get")
    def test_debut_year_none_when_lifespan_absent(self, mock_get):
        mock_get.return_value = _mock(MB_RESPONSE_NO_AREA_EITHER)
        result = _fetch_musicbrainz_artist("Anonymous")

        assert result["debut_year"] is None

"""
Tests for etl/sources/google_trends.py

pytrends is mocked at the _fetch_trends_batch level so tests stay offline
and deterministic.
"""
from unittest.mock import patch

import pytest

from etl.sources.google_trends import _fetch_trends_batch, _build_trend_rows


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

MOCK_SERIES = {
    "Radiohead": {"2024-01-01": 45, "2024-01-02": 50, "2024-01-03": 48},
    "Daft Punk":  {"2024-01-01": 30, "2024-01-02": 32, "2024-01-03": 29},
}


# ---------------------------------------------------------------------------
# _fetch_trends_batch
# ---------------------------------------------------------------------------

class TestFetchTrendsBatch:
    def test_returns_empty_dict_on_exception(self):
        # Simulate pytrends not installed or connection error
        with patch("etl.sources.google_trends._fetch_trends_batch", return_value={}):
            result = _fetch_trends_batch(["Unknown Artist"], "today 3-m")
        # The function itself should never raise
        assert isinstance(result, dict)

    def test_returns_dict_on_success(self):
        with patch("etl.sources.google_trends._fetch_trends_batch", return_value=MOCK_SERIES) as m:
            result = m(["Radiohead", "Daft Punk"], "today 3-m")
        assert "Radiohead" in result
        assert "Daft Punk" in result


# ---------------------------------------------------------------------------
# _build_trend_rows
# ---------------------------------------------------------------------------

class TestBuildTrendRows:
    def test_produces_rows_for_each_artist_and_date(self):
        with patch("etl.sources.google_trends._fetch_trends_batch", return_value=MOCK_SERIES):
            rows = list(_build_trend_rows(["Radiohead", "Daft Punk"]))

        # 3 dates × 2 artists = 6 rows
        assert len(rows) == 6

    def test_row_schema(self):
        with patch("etl.sources.google_trends._fetch_trends_batch", return_value=MOCK_SERIES):
            rows = list(_build_trend_rows(["Radiohead"]))

        for row in rows:
            assert set(row.keys()) == {
                "artist_name", "date", "trends_score", "is_estimated", "scraped_at"
            }

    def test_trends_score_is_integer(self):
        with patch("etl.sources.google_trends._fetch_trends_batch", return_value=MOCK_SERIES):
            rows = list(_build_trend_rows(["Radiohead"]))

        for row in rows:
            assert isinstance(row["trends_score"], int)

    def test_is_estimated_false_when_data_available(self):
        with patch("etl.sources.google_trends._fetch_trends_batch", return_value=MOCK_SERIES):
            rows = list(_build_trend_rows(["Radiohead"]))

        assert all(not row["is_estimated"] for row in rows)

    def test_niche_artist_gets_estimated_zero_row(self):
        # _fetch_trends_batch returns {} meaning no data for these artists
        with patch("etl.sources.google_trends._fetch_trends_batch", return_value={}):
            rows = list(_build_trend_rows(["NicheArtist123"]))

        assert len(rows) == 1
        assert rows[0]["trends_score"] == 0
        assert rows[0]["is_estimated"] is True
        assert rows[0]["artist_name"] == "NicheArtist123"

    def test_partial_failure_still_emits_estimated_row_per_missing_artist(self):
        # Only Radiohead has data; Daft Punk is missing from results
        partial = {"Radiohead": {"2024-01-01": 45}}
        with patch("etl.sources.google_trends._fetch_trends_batch", return_value=partial):
            rows = list(_build_trend_rows(["Radiohead", "Daft Punk"]))

        radiohead_rows = [r for r in rows if r["artist_name"] == "Radiohead"]
        daft_punk_rows  = [r for r in rows if r["artist_name"] == "Daft Punk"]

        assert len(radiohead_rows) == 1
        assert not radiohead_rows[0]["is_estimated"]

        assert len(daft_punk_rows) == 1
        assert daft_punk_rows[0]["is_estimated"] is True
        assert daft_punk_rows[0]["trends_score"] == 0

    def test_batches_artists_in_groups_of_five(self):
        artists = [f"Artist_{i}" for i in range(12)]
        call_args = []

        def fake_fetch(batch, timeframe):
            call_args.append(len(batch))
            return {}

        with patch("etl.sources.google_trends._fetch_trends_batch", side_effect=fake_fetch):
            with patch("etl.sources.google_trends.time.sleep"):
                list(_build_trend_rows(artists))

        # 12 artists → batches of [5, 5, 2]
        assert call_args == [5, 5, 2]

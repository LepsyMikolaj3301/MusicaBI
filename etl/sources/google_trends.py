import time
from typing import Iterator
from datetime import datetime, timezone

import dlt

_BATCH_SIZE = 5   # Google Trends max keywords per request
_BATCH_DELAY_SEC = 1.0


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fetch_trends_batch(artist_names: list[str], timeframe: str) -> dict[str, dict[str, int]]:
    """Return {artist_name: {date_str: score}} for one batch.

    Returns {} on any error (rate-limits, captcha, network) so callers can
    fall back to is_estimated=True rows without crashing the pipeline.
    """
    try:
        from pytrends.request import TrendReq

        pytrends = TrendReq(hl="en-US", tz=0)
        pytrends.build_payload(artist_names, timeframe=timeframe, geo="")
        df = pytrends.interest_over_time()
        if df.empty:
            return {}
        df = df.drop(columns=["isPartial"], errors="ignore")
        return {
            col: {
                (d.date().isoformat() if hasattr(d, "date") else str(d)): int(score)
                for d, score in df[col].items()
            }
            for col in df.columns
        }
    except Exception:
        return {}


def _build_trend_rows(
    artist_names: list, timeframe: str = "today 3-m"
) -> Iterator[dict]:
    scraped_at = datetime.now(timezone.utc).isoformat()

    for i in range(0, len(artist_names), _BATCH_SIZE):
        batch = artist_names[i : i + _BATCH_SIZE]
        results = _fetch_trends_batch(batch, timeframe)

        for name in batch:
            series = results.get(name)
            if series:
                for date_str, score in series.items():
                    yield {
                        "artist_name": name,
                        "date": date_str,
                        "trends_score": score,
                        "is_estimated": False,
                        "scraped_at": scraped_at,
                    }
            else:
                # niche artist or API unavailable — insert a zero row and flag it
                yield {
                    "artist_name": name,
                    "date": datetime.now(timezone.utc).date().isoformat(),
                    "trends_score": 0,
                    "is_estimated": True,
                    "scraped_at": scraped_at,
                }

        if i + _BATCH_SIZE < len(artist_names):
            time.sleep(_BATCH_DELAY_SEC)


# ---------------------------------------------------------------------------
# dlt source + resources
# ---------------------------------------------------------------------------

@dlt.source(name="google_trends")
def google_trends_source(artist_names: list | None = None):
    return (google_trends_daily(artist_names or []),)


@dlt.resource(
    name="stg_google_trends",
    # merge so same (artist, date) pair is upserted, not duplicated on reruns
    write_disposition="merge",
    primary_key=["artist_name", "date"],
)
def google_trends_daily(artist_names: list) -> Iterator[dict]:
    yield from _build_trend_rows(artist_names)

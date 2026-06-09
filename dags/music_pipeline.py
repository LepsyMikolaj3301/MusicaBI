"""
Airflow DAG: full music ETL pipeline

Ingests from Last.fm, Spotify, MusicBrainz, and Google Trends into the
staging schema in Postgres. All four ingest tasks run in parallel since
their staging tables are independent.

Prerequisites (Airflow container):
  - dlt[postgres] and pytrends installed in the image
  - etl package importable (installed via `pip install -e .` or PYTHONPATH)
  - .dlt/config.toml and .dlt/secrets.toml accessible at runtime
"""
import logging
from datetime import datetime

from airflow.decorators import dag, task

log = logging.getLogger(__name__)


@dag(
    dag_id="music_pipeline",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["lastfm", "spotify", "musicbrainz", "google_trends", "dlt", "etl"],
)
def music_pipeline():
    def _artist_names() -> list:
        import dlt
        return list(dlt.config.get("pipeline.artist_names") or [])

    @task()
    def ingest_lastfm() -> None:
        from etl.pipeline import run_lastfm
        run_lastfm(_artist_names())

    @task()
    def ingest_spotify() -> None:
        from etl.pipeline import run_spotify
        run_spotify(_artist_names())

    @task()
    def ingest_musicbrainz() -> None:
        from etl.pipeline import run_musicbrainz
        run_musicbrainz(_artist_names())

    @task()
    def ingest_google_trends() -> None:
        from etl.pipeline import run_google_trends
        run_google_trends(_artist_names())

    # All four run in parallel — no inter-source dependencies at ingest stage
    ingest_lastfm()
    ingest_spotify()
    ingest_musicbrainz()
    ingest_google_trends()


music_pipeline()

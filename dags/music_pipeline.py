"""
Airflow DAG: full music ETL pipeline

Ingests from Last.fm, Spotify, and MusicBrainz into the staging schema in
Postgres. All three ingest tasks run in parallel since their staging tables
are independent.

Prerequisites (Airflow container):
  - dlt[postgres] installed in the image
  - etl package importable (installed via `pip install -e .` or PYTHONPATH)
  - .dlt/config.toml and .dlt/secrets.toml accessible at runtime
"""
import logging
from datetime import datetime

from airflow.decorators import dag, task
from airflow.operators.bash import BashOperator

log = logging.getLogger(__name__)


@dag(
    dag_id="music_pipeline",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["lastfm", "spotify", "musicbrainz", "dlt", "etl"],
)
def music_pipeline():
    def _artist_names() -> list:
        try:
            from etl.pipeline import load_artists_from_file
            artists = load_artists_from_file()
            if artists:
                return artists
        except Exception:
            pass
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

    # All three ingest tasks run in parallel — no inter-source dependencies.
    # run_transforms waits for all of them so dbt sees a consistent staging snapshot.
    t_lastfm = ingest_lastfm()
    t_spotify = ingest_spotify()
    t_musicbrainz = ingest_musicbrainz()

    run_transforms = BashOperator(
        task_id="run_transforms",
        bash_command="cd /opt/airflow/transform && dbt run --profiles-dir .",
    )

    [t_lastfm, t_spotify, t_musicbrainz] >> run_transforms


music_pipeline()

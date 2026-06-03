from datetime import datetime
import logging

from airflow.decorators import dag, task

log = logging.getLogger(__name__)


@dag(
    dag_id="lastfm_pipeline",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["lastfm", "dlt", "etl"],
)
def lastfm_pipeline():
    @task()
    def ingest_lastfm() -> None:
        """Load Last.fm chart data into the staging schema via dlt.

        TODO: install dlt[postgres] in the Airflow image and mount / install
        the etl package, then replace the stub below with:
            from etl.pipeline import run
            run()
        """
        log.info("Placeholder: would run dlt pipeline 'lastfm_to_staging' here")

    @task()
    def transform_staging() -> None:
        """Transform tables in the staging schema into the warehouse/mart layer.

        TODO: implement SQL or dbt transformations that read from staging.*
        and write into the mart/warehouse schema.
        """
        log.info("Placeholder: would run staging → mart transformations here")

    ingest_lastfm() >> transform_staging()


lastfm_pipeline()

import dlt

from etl.sources.lastfm import lastfm_source
from etl.sources.spotify import spotify_source
from etl.sources.musicbrainz import musicbrainz_source
from etl.sources.google_trends import google_trends_source


def _make_pipeline(name: str):
    return dlt.pipeline(
        pipeline_name=name,
        destination="postgres",
        dataset_name="staging",
    )


def _log(load_info) -> None:
    print(load_info)
    for package in load_info.load_packages:
        for job in package.jobs.get("failed_jobs", []):
            print(f"FAILED: {job.job_file_path} — {job.failed_message}")


def run_lastfm(artist_names: list) -> None:
    pipeline = _make_pipeline("lastfm_to_staging")
    _log(pipeline.run(lastfm_source(artist_names=artist_names)))


def run_spotify(artist_names: list) -> None:
    pipeline = _make_pipeline("spotify_to_staging")
    _log(pipeline.run(spotify_source(artist_names=artist_names)))


def run_musicbrainz(artist_names: list) -> None:
    pipeline = _make_pipeline("musicbrainz_to_staging")
    _log(pipeline.run(musicbrainz_source(artist_names=artist_names)))


def run_google_trends(artist_names: list) -> None:
    pipeline = _make_pipeline("google_trends_to_staging")
    _log(pipeline.run(google_trends_source(artist_names=artist_names)))


def run_all() -> None:
    artist_names: list = list(dlt.config.get("pipeline.artist_names") or [])
    run_lastfm(artist_names)
    run_spotify(artist_names)
    run_musicbrainz(artist_names)
    run_google_trends(artist_names)


if __name__ == "__main__":
    run_all()

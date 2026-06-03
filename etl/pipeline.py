import dlt
from sources.lastfm import lastfm_source


def run() -> None:
    pipeline = dlt.pipeline(
        pipeline_name="lastfm_to_staging",
        destination="postgres",
        dataset_name="staging",
    )

    source = lastfm_source()
    load_info = pipeline.run(source)

    print(load_info)
    for package in load_info.load_packages:
        for job in package.jobs["failed_jobs"]:
            print(f"FAILED: {job.job_file_path} — {job.failed_message}")


if __name__ == "__main__":
    run()

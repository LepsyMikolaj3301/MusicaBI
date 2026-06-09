# Using the official Airflow 3 image
FROM apache/airflow:3.0.0

# Install the MSSQL provider and necessary drivers
# We use the 'airflow' user to ensure permissions are correct
USER airflow
RUN pip install --no-cache-dir \
    pandas \
    sqlalchemy \
    duckdb \
    "dlt[postgres]>=1.4.0" \
    "pytrends>=4.9.0" \
    "dbt-core>=1.8.0" \
    "dbt-postgres>=1.8.0" \
 && mkdir -p /home/airflow/.dlt/pipelines
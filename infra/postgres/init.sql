-- Ensure the staging schema exists for dlt to load into.
-- The database itself is created automatically via POSTGRES_DB env var.
CREATE SCHEMA IF NOT EXISTS staging;
GRANT ALL ON SCHEMA staging TO admin;

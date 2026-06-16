-- Databricks notebook source
-- ============================================================================
-- 01_ingest_dataset — load the healthcare facility dataset into facility_raw
-- ============================================================================
-- Source: the hackathon-provided healthcare-facility dataset (the same shape as
-- data/facilities_sample.csv). Land it as a Delta table in the `caregap` schema,
-- then expose a cleaned view that lower/trims the text columns so downstream
-- keyword matching (notebook 02) is case- and whitespace-insensitive — matching
-- the _norm() behaviour in src/evidence.py.
-- ============================================================================

-- COMMAND ----------

CREATE SCHEMA IF NOT EXISTS caregap;
USE caregap;

-- COMMAND ----------

-- Define the table up front so COPY INTO has a target with an explicit schema.
-- See sql/databricks_tables.sql for the canonical definition.
CREATE TABLE IF NOT EXISTS caregap.facility_raw (
  facility_id     STRING,
  name            STRING,
  address         STRING,
  state           STRING,
  district        STRING,
  latitude        DOUBLE,
  longitude       DOUBLE,
  description     STRING,
  capability      STRING,
  procedure       STRING,
  equipment       STRING,
  specialties     STRING,
  source_urls     STRING,
  numberDoctors   INT,
  capacity        INT,
  yearEstablished INT
)
USING DELTA;

-- COMMAND ----------

-- Idempotent bulk load from the hackathon-provided dataset (CSV in a volume /
-- cloud path). COPY INTO only ingests new files, so re-running is safe.
-- Adjust the FROM path to the workspace volume holding the provided dataset.
COPY INTO caregap.facility_raw
FROM '/Volumes/main/caregap/landing/facilities/'   -- hackathon-provided dataset location
FILEFORMAT = CSV
FORMAT_OPTIONS (
  'header'           = 'true',
  'inferSchema'      = 'false',
  'multiLine'        = 'true',
  'escape'           = '"',
  'nullValue'        = '',
  'mode'             = 'PERMISSIVE'
)
COPY_OPTIONS ('mergeSchema' = 'false');

-- COMMAND ----------

-- Alternative one-shot pattern (full replace) if you prefer CREATE TABLE AS over
-- incremental COPY INTO. Reads the same hackathon-provided dataset path.
-- CREATE OR REPLACE TABLE caregap.facility_raw AS
-- SELECT
--   CAST(facility_id     AS STRING) AS facility_id,
--   CAST(name            AS STRING) AS name,
--   CAST(address         AS STRING) AS address,
--   CAST(state           AS STRING) AS state,
--   CAST(district        AS STRING) AS district,
--   CAST(latitude        AS DOUBLE) AS latitude,
--   CAST(longitude       AS DOUBLE) AS longitude,
--   CAST(description     AS STRING) AS description,
--   CAST(capability      AS STRING) AS capability,
--   CAST(procedure       AS STRING) AS procedure,
--   CAST(equipment       AS STRING) AS equipment,
--   CAST(specialties     AS STRING) AS specialties,
--   CAST(source_urls     AS STRING) AS source_urls,
--   CAST(numberDoctors   AS INT)    AS numberDoctors,
--   CAST(capacity        AS INT)    AS capacity,
--   CAST(yearEstablished AS INT)    AS yearEstablished
-- FROM read_files(
--   '/Volumes/main/caregap/landing/facilities/',
--   format => 'csv', header => true, multiLine => true
-- );

-- COMMAND ----------

-- Cleaned, normalized view: lower/trim every text column the scorer reads, and
-- collapse internal whitespace (mirrors _norm() in src/evidence.py). Numeric and
-- geo columns pass through unchanged. Downstream notebooks read THIS view.
CREATE OR REPLACE VIEW caregap.facility_clean AS
SELECT
  facility_id,
  name,
  address,
  trim(lower(state))                        AS state,
  trim(lower(district))                     AS district,
  latitude,
  longitude,
  trim(lower(regexp_replace(coalesce(description, ''), '\\s+', ' '))) AS description,
  trim(lower(regexp_replace(coalesce(capability,  ''), '\\s+', ' '))) AS capability,
  trim(lower(regexp_replace(coalesce(procedure,   ''), '\\s+', ' '))) AS procedure,
  trim(lower(regexp_replace(coalesce(equipment,   ''), '\\s+', ' '))) AS equipment,
  trim(lower(regexp_replace(coalesce(specialties, ''), '\\s+', ' '))) AS specialties,
  trim(coalesce(source_urls, ''))           AS source_urls,
  numberDoctors,
  capacity,
  yearEstablished
FROM caregap.facility_raw;

-- COMMAND ----------

-- Sanity checks.
SELECT count(*) AS facilities_ingested FROM caregap.facility_raw;
-- SELECT * FROM caregap.facility_clean LIMIT 20;

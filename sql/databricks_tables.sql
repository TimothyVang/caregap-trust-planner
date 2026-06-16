-- ============================================================================
-- CareGap Trust Planner — Databricks analytics tables (Delta / Unity Catalog)
-- ============================================================================
-- These are the heavy-analytics tables. They live in Databricks SQL as managed
-- Delta tables under a `caregap` schema in Unity Catalog. Planner *actions*
-- (saved scenarios, shortlists, notes, overrides, review decisions, audit) live
-- separately in Lakebase (managed Postgres) — see sql/lakebase_schema.sql.
--
-- Catalog/schema convention (qualify as <catalog>.caregap.<table> in practice):
--   CREATE SCHEMA IF NOT EXISTS caregap;
--   USE caregap;
-- All tables below are written to the `caregap` schema. The CREATE TABLE
-- statements use bare names so they can be run after `USE caregap;`, or be
-- prefixed with `caregap.` (or `<catalog>.caregap.`) as needed.
--
-- Pipeline that populates these tables:
--   notebooks/01_ingest_dataset.sql   -> caregap.facility_raw
--   notebooks/02_extract_claims.sql   -> caregap.facility_claims, caregap.facility_evidence
--   notebooks/03_score_facilities.sql -> caregap.facility_scores, caregap.referral_candidates
--   notebooks/04_score_regions.sql    -> caregap.regional_gap_scores
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS caregap
  COMMENT 'CareGap Trust Planner analytics schema (Delta / Unity Catalog).';

-- ----------------------------------------------------------------------------
-- facility_raw
-- Raw, ingested healthcare-facility records (the hackathon-provided dataset).
-- Mirrors the columns in data/facilities_sample.csv and src/data_loader.py.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS caregap.facility_raw (
  facility_id     STRING  COMMENT 'Stable facility identifier (e.g. MH-MUM-001).',
  name            STRING  COMMENT 'Facility display name.',
  address         STRING  COMMENT 'Free-text street address.',
  state           STRING  COMMENT 'State / province.',
  district        STRING  COMMENT 'District within the state.',
  latitude        DOUBLE  COMMENT 'Geographic latitude (decimal degrees).',
  longitude       DOUBLE  COMMENT 'Geographic longitude (decimal degrees).',
  description     STRING  COMMENT 'Free-text description; scanned for capability + negation evidence.',
  capability      STRING  COMMENT 'Semicolon-separated claimed capabilities.',
  procedure       STRING  COMMENT 'Semicolon-separated procedures offered.',
  equipment       STRING  COMMENT 'Semicolon-separated equipment available.',
  specialties     STRING  COMMENT 'Semicolon-separated clinical specialties.',
  source_urls     STRING  COMMENT 'Source URL(s) backing the record; presence boosts trust.',
  numberDoctors   INT     COMMENT 'Reported number of doctors.',
  capacity        INT     COMMENT 'Reported bed / patient capacity.',
  yearEstablished INT     COMMENT 'Year the facility was established.'
)
USING DELTA
COMMENT 'Raw ingested facility records (caregap schema). Source: hackathon-provided dataset.';

-- ----------------------------------------------------------------------------
-- facility_claims
-- One row per detected capability claim, with the field and span it came from.
-- The "show your work" provenance for each capability assertion.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS caregap.facility_claims (
  claim_id              STRING    COMMENT 'Surrogate claim identifier.',
  facility_id           STRING    COMMENT 'FK -> facility_raw.facility_id.',
  capability_type       STRING    COMMENT 'One of: emergency_maternity, icu, dialysis, trauma, oncology, nicu.',
  claim_text            STRING    COMMENT 'The matched keyword / phrase asserting the capability.',
  claim_source_field    STRING    COMMENT 'Source field: capability|procedure|equipment|specialties|description.',
  extracted_evidence_span STRING  COMMENT 'Short snippet of original text around the match.',
  extraction_method     STRING    COMMENT 'How the claim was extracted (e.g. keyword_match).',
  created_at            TIMESTAMP COMMENT 'Extraction timestamp.'
)
USING DELTA
COMMENT 'Per-claim capability evidence with field-level provenance (caregap schema).';

-- ----------------------------------------------------------------------------
-- facility_evidence
-- Granular keyword hits backing the scoring components (one row per keyword/field).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS caregap.facility_evidence (
  evidence_id     STRING COMMENT 'Surrogate evidence identifier.',
  facility_id     STRING COMMENT 'FK -> facility_raw.facility_id.',
  capability_type STRING COMMENT 'Capability the evidence supports.',
  field           STRING COMMENT 'Field scanned: capability|procedure|equipment|specialties|description.',
  keyword         STRING COMMENT 'Matched capability keyword.',
  snippet         STRING COMMENT 'Snippet of original text around the keyword.'
)
USING DELTA
COMMENT 'Keyword-level evidence hits per facility/capability (caregap schema).';

-- ----------------------------------------------------------------------------
-- facility_scores
-- Per-facility, per-capability trust score + label (mirrors src/scoring.py).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS caregap.facility_scores (
  facility_id       STRING  COMMENT 'FK -> facility_raw.facility_id.',
  capability_type   STRING  COMMENT 'Capability scored.',
  trust_score       INT     COMMENT 'Weighted trust score, clamped 0..100.',
  trust_label       STRING  COMMENT 'Strong/Partial/Weak/Very weak/No usable/Contradictory evidence.',
  contradiction_flag BOOLEAN COMMENT 'True when claimed-but-unsupported or negated.',
  missing_fields    STRING  COMMENT 'Comma-separated critical fields missing (procedure, equipment).',
  explanation       STRING  COMMENT 'Human-readable explanation of the label.'
)
USING DELTA
COMMENT 'Per-facility capability trust scores (caregap schema). Mirrors src/scoring.py.';

-- ----------------------------------------------------------------------------
-- regional_gap_scores
-- Per-region (state-district) aggregate planning verdict + desert label.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS caregap.regional_gap_scores (
  region_id               STRING COMMENT 'Region key, state||"-"||district.',
  capability_type         STRING COMMENT 'Capability the region is assessed for.',
  facilities_total        INT    COMMENT 'Total facilities considered in the region.',
  strong_facilities       INT    COMMENT 'Count labelled Strong evidence.',
  partial_facilities      INT    COMMENT 'Count labelled Partial evidence.',
  weak_facilities         INT    COMMENT 'Count labelled Weak + Very weak evidence.',
  contradictory_facilities INT   COMMENT 'Count labelled Contradictory evidence.',
  data_completeness_score DOUBLE COMMENT 'Mean record completeness 0..1.',
  planning_confidence     DOUBLE COMMENT 'Planning confidence 0..100.',
  desert_label            STRING COMMENT 'Likely care desert / Data-poor area / Sufficient evidence / Contradictory region.'
)
USING DELTA
COMMENT 'Per-region care-gap aggregates and desert labels (caregap schema). Mirrors score_region().';

-- ----------------------------------------------------------------------------
-- referral_candidates
-- Trusted facilities, ready for the referral / routing tab (with geo).
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS caregap.referral_candidates (
  facility_id     STRING COMMENT 'FK -> facility_raw.facility_id.',
  capability_type STRING COMMENT 'Capability the facility can serve.',
  trust_label     STRING COMMENT 'Trust label (typically Strong / Partial evidence).',
  trust_score     INT    COMMENT 'Trust score 0..100.',
  latitude        DOUBLE COMMENT 'Latitude for distance / map routing.',
  longitude       DOUBLE COMMENT 'Longitude for distance / map routing.'
)
USING DELTA
COMMENT 'Evidenced referral targets with coordinates (caregap schema).';

-- Databricks notebook source
-- ============================================================================
-- 04_score_regions — aggregate facility_scores into regional_gap_scores
-- ============================================================================
-- Mirrors src/scoring.py::score_region. Region key = state || '-' || district.
-- For each (region_id, capability_type):
--
--   trust_weighted_supply = sum over facilities of LABEL_SUPPLY_WEIGHT:
--       Strong=1.0, Partial=0.6, Weak=0.3, Very weak=0.1,
--       No usable=0.0, Contradictory=0.0
--   (Note: the regional_gap_scores.weak_facilities COUNT combines Weak + Very
--    weak, exactly like score_region; the supply SUM keeps their distinct
--    weights 0.3 vs 0.1.)
--
--   evidence_coverage   = (strong + partial) / total
--   data_completeness   = mean record completeness over facilities (0..1)
--   url_coverage        = share of facilities with a source URL
--   contradiction_rate  = contradictory / total
--   sparse_record_rate  = share of facilities with completeness < 0.5
--
--   planning_confidence = clamp(0..100) of 100 * (
--         0.35*evidence_coverage + 0.25*data_completeness + 0.20*url_coverage
--       - 0.10*contradiction_rate - 0.30*sparse_record_rate + 0.30 )
--
--   desert_label (order matters, first match wins; total=0 -> 'Data-poor area'):
--       contradiction_rate >= 0.34                      -> 'Contradictory region'
--       supply >= 1.5  AND confidence >= 40             -> 'Sufficient evidence'
--       supply < 1.0   AND confidence >= 40             -> 'Likely care desert'
--       supply < 1.0   AND confidence <  40             -> 'Data-poor area'
--       else: confidence >= 40 ? 'Sufficient evidence' : 'Data-poor area'
--
-- Completeness uses COMPLETENESS_FIELDS from src/capabilities.py:
--   description, capability, procedure, equipment, specialties, source_urls,
--   numberDoctors, latitude, longitude  (9 fields).
-- ============================================================================

-- COMMAND ----------

USE caregap;

-- COMMAND ----------

-- Per-facility record completeness (0..1) over the 9 COMPLETENESS_FIELDS.
-- A field counts as present when its trimmed string form is non-empty; for the
-- numeric/geo fields a non-null value counts as present (matches _is_present on
-- the stringified value in src/scoring.py).
CREATE OR REPLACE TEMP VIEW facility_completeness AS
SELECT
  facility_id,
  state,
  district,
  ( CASE WHEN description   IS NOT NULL AND trim(description)   <> '' THEN 1 ELSE 0 END
  + CASE WHEN capability    IS NOT NULL AND trim(capability)    <> '' THEN 1 ELSE 0 END
  + CASE WHEN procedure     IS NOT NULL AND trim(procedure)     <> '' THEN 1 ELSE 0 END
  + CASE WHEN equipment     IS NOT NULL AND trim(equipment)     <> '' THEN 1 ELSE 0 END
  + CASE WHEN specialties   IS NOT NULL AND trim(specialties)   <> '' THEN 1 ELSE 0 END
  + CASE WHEN source_urls   IS NOT NULL AND trim(source_urls)   <> '' THEN 1 ELSE 0 END
  + CASE WHEN numberDoctors IS NOT NULL THEN 1 ELSE 0 END
  + CASE WHEN latitude      IS NOT NULL THEN 1 ELSE 0 END
  + CASE WHEN longitude     IS NOT NULL THEN 1 ELSE 0 END
  ) / 9.0 AS completeness
FROM caregap.facility_clean;

-- COMMAND ----------

-- Join each scored capability row to its facility's region + completeness, and
-- attach the label supply weight and url-present flag.
CREATE OR REPLACE TEMP VIEW scored_with_region AS
SELECT
  concat(fc.state, '-', fc.district) AS region_id,
  s.capability_type,
  s.facility_id,
  s.trust_label,
  fcomp.completeness,
  CASE WHEN fc.source_urls IS NOT NULL AND trim(fc.source_urls) <> '' THEN 1 ELSE 0 END AS url_present,
  CASE s.trust_label
    WHEN 'Strong evidence'        THEN 1.0
    WHEN 'Partial evidence'       THEN 0.6
    WHEN 'Weak evidence'          THEN 0.3
    WHEN 'Very weak evidence'     THEN 0.1
    WHEN 'No usable evidence'     THEN 0.0
    WHEN 'Contradictory evidence' THEN 0.0
    ELSE 0.0
  END AS supply_weight
FROM caregap.facility_scores s
JOIN caregap.facility_clean fc      ON fc.facility_id = s.facility_id
JOIN facility_completeness fcomp    ON fcomp.facility_id = s.facility_id;

-- COMMAND ----------

-- Region-level aggregates, then derived rates, confidence, and desert label.
CREATE OR REPLACE TABLE caregap.regional_gap_scores AS
WITH agg AS (
  SELECT
    region_id,
    capability_type,
    count(*)                                                                        AS facilities_total,
    sum(CASE WHEN trust_label = 'Strong evidence'        THEN 1 ELSE 0 END)         AS strong_facilities,
    sum(CASE WHEN trust_label = 'Partial evidence'       THEN 1 ELSE 0 END)         AS partial_facilities,
    sum(CASE WHEN trust_label IN ('Weak evidence','Very weak evidence') THEN 1 ELSE 0 END) AS weak_facilities,
    sum(CASE WHEN trust_label = 'Contradictory evidence' THEN 1 ELSE 0 END)         AS contradictory_facilities,
    sum(supply_weight)                                                              AS trust_weighted_supply,
    avg(completeness)                                                               AS data_completeness_score,
    avg(url_present)                                                                AS url_coverage,
    avg(CASE WHEN completeness < 0.5 THEN 1.0 ELSE 0.0 END)                         AS sparse_record_rate
  FROM scored_with_region
  GROUP BY region_id, capability_type
),
rates AS (
  SELECT
    *,
    (strong_facilities + partial_facilities) / facilities_total AS evidence_coverage,
    contradictory_facilities / facilities_total                 AS contradiction_rate
  FROM agg
),
conf AS (
  SELECT
    *,
    greatest(0.0, least(100.0,
      100.0 * (
          0.35 * evidence_coverage
        + 0.25 * data_completeness_score
        + 0.20 * url_coverage
        - 0.10 * contradiction_rate
        - 0.30 * sparse_record_rate
        + 0.30
      )
    )) AS planning_confidence
  FROM rates
)
SELECT
  region_id,
  capability_type,
  CAST(facilities_total         AS INT)    AS facilities_total,
  CAST(strong_facilities        AS INT)    AS strong_facilities,
  CAST(partial_facilities       AS INT)    AS partial_facilities,
  CAST(weak_facilities          AS INT)    AS weak_facilities,
  CAST(contradictory_facilities AS INT)    AS contradictory_facilities,
  round(data_completeness_score, 2)        AS data_completeness_score,
  round(planning_confidence, 1)            AS planning_confidence,
  -- desert_label: evaluate in the same priority order as _desert_label()
  CASE
    WHEN contradiction_rate >= 0.34                                          THEN 'Contradictory region'
    WHEN trust_weighted_supply >= 1.5 AND planning_confidence >= 40          THEN 'Sufficient evidence'
    WHEN trust_weighted_supply <  1.0 AND planning_confidence >= 40          THEN 'Likely care desert'
    WHEN trust_weighted_supply <  1.0 AND planning_confidence <  40          THEN 'Data-poor area'
    WHEN planning_confidence >= 40                                           THEN 'Sufficient evidence'
    ELSE 'Data-poor area'
  END AS desert_label
FROM conf;

-- COMMAND ----------

-- Sanity checks.
SELECT desert_label, count(*) AS regions
FROM caregap.regional_gap_scores
GROUP BY desert_label
ORDER BY desert_label;

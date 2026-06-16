-- Databricks notebook source
-- ============================================================================
-- 03_score_facilities — compute facility_scores (and referral_candidates)
-- ============================================================================
-- Implements the exact additive trust formula from src/scoring.py::score_facility:
--
--   trust_score =
--       25 * capability_match            (WEIGHTS.capability)
--     + 20 * procedure_match             (WEIGHTS.procedure)
--     + 20 * equipment_match             (WEIGHTS.equipment)
--     + 15 * specialty_match             (WEIGHTS.specialty)
--     + 15 * description_match           (WEIGHTS.description)
--     +  5 * source_url_present          (WEIGHTS.source_url)
--     - 20 * contradiction_penalty       (PENALTIES.contradiction)
--     - 10 * vague_language_penalty      (PENALTIES.vague)
--     - 10 * missing_critical_penalty    (PENALTIES.missing_critical)
--   clamped to 0..100.
--
-- Each *_match is 1 if any capability keyword appears in that field, else 0.
--   description_match uses the *capability* keyword set (per FIELD_FOR_COMPONENT).
--
-- contradiction_flag (src/scoring.py) =
--   has_negation_contradiction  OR  (capability_match=1 AND procedure=0 AND equipment=0).
--   has_negation_contradiction: a capability term appears in description with a
--   negation cue within ~40 chars (no/not/non-/without/unavailable/absent/
--   lacks/lacking/closed/out of service/not functional/non functional/defunct).
--
-- vague penalty: there is a capability mention in description+capability+procedure
--   AND a hedging term (may/might/sometimes/occasionally/limited/basic/general/
--   planned/proposed/upcoming/if available/on request/referral only).
--
-- missing_critical penalty: capability_match=1 AND a critical field
--   (procedure or equipment) is empty.
--
-- Labels: 80-100 Strong, 55-79 Partial, 30-54 Weak, 1-29 Very weak, 0 No usable;
--   contradiction_flag overrides the band with 'Contradictory evidence'.
-- ============================================================================

-- COMMAND ----------

USE caregap;

-- COMMAND ----------

-- Capability rows to score: every facility x every capability_type. (Cross join
-- with the 6 known capabilities; scoring a facility for a capability it doesn't
-- claim simply yields a low/zero score, which is the desired signal.)
CREATE OR REPLACE TEMP VIEW capability_universe AS
SELECT explode(array(
  'emergency_maternity','icu','dialysis','trauma','oncology','nicu'
)) AS capability_type;

-- COMMAND ----------

-- Per-component matches (0/1) by aggregating evidence from notebook 02, plus the
-- raw normalized fields needed for negation / vague / missing-field logic.
CREATE OR REPLACE TEMP VIEW facility_components AS
SELECT
  fc.facility_id,
  cu.capability_type,
  fc.description,
  fc.capability,
  fc.procedure,
  fc.equipment,
  fc.specialties,
  fc.source_urls,
  fc.latitude,
  fc.longitude,
  -- match flags: did any evidence hit land in this field for this capability?
  MAX(CASE WHEN ev.field = 'capability'  THEN 1 ELSE 0 END) AS capability_match,
  MAX(CASE WHEN ev.field = 'procedure'   THEN 1 ELSE 0 END) AS procedure_match,
  MAX(CASE WHEN ev.field = 'equipment'   THEN 1 ELSE 0 END) AS equipment_match,
  MAX(CASE WHEN ev.field = 'specialties' THEN 1 ELSE 0 END) AS specialty_match,
  MAX(CASE WHEN ev.field = 'description' THEN 1 ELSE 0 END) AS description_match
FROM caregap.facility_clean fc
CROSS JOIN capability_universe cu
LEFT JOIN caregap.facility_evidence ev
  ON ev.facility_id = fc.facility_id
 AND ev.capability_type = cu.capability_type
GROUP BY
  fc.facility_id, cu.capability_type, fc.description, fc.capability, fc.procedure,
  fc.equipment, fc.specialties, fc.source_urls, fc.latitude, fc.longitude;

-- COMMAND ----------

-- Negation contradiction: a capability term in the description sits within ~40
-- chars of a negation cue. We approximate the Python ~40-char window with a
-- regex that allows up to 40 chars between negation and capability term in
-- either order, evaluated over the (already-lowercased) description. The
-- capability-term alternations mirror src/capabilities.py capability lists.
CREATE OR REPLACE TEMP VIEW facility_negation AS
SELECT
  facility_id,
  capability_type,
  CASE
    WHEN description IS NULL OR description = '' THEN 0
    -- negation cue followed (within 40 chars) by a capability term, OR vice versa
    WHEN description RLIKE concat(
           '(', neg_cues, ').{0,40}(', cap_terms, ')'
         )
      OR description RLIKE concat(
           '(', cap_terms, ').{0,40}(', neg_cues, ')'
         )
    THEN 1 ELSE 0
  END AS negation_contradiction
FROM (
  SELECT
    fc.facility_id,
    cu.capability_type,
    fc.description,
    -- negation cues (NEGATION_TERMS); spaces in cues like 'no ' are intentional.
    'no |not |non-|without|unavailable|absent|lacks|lacking|closed|out of service|not functional|non functional|defunct' AS neg_cues,
    -- capability terms per capability_type (CAPABILITIES[*].capability).
    CASE cu.capability_type
      WHEN 'emergency_maternity' THEN 'maternity|obstetric|obstetrics|emergency obstetric|labour|delivery|cemonc|bemonc'
      WHEN 'icu'      THEN 'icu|intensive care|critical care'
      WHEN 'dialysis' THEN 'dialysis|haemodialysis|hemodialysis|renal replacement'
      WHEN 'trauma'   THEN 'trauma|emergency|casualty|accident'
      WHEN 'oncology' THEN 'oncology|cancer|tumour|tumor'
      WHEN 'nicu'     THEN 'nicu|neonatal intensive care|newborn care|sncu'
    END AS cap_terms
  FROM caregap.facility_clean fc
  CROSS JOIN capability_universe cu
) base;

-- COMMAND ----------

-- Vague language: a capability mention exists across description+capability+
-- procedure AND a hedging term appears in that combined blob.
CREATE OR REPLACE TEMP VIEW facility_vague AS
SELECT
  fc.facility_id,
  cu.capability_type,
  CASE
    WHEN blob RLIKE concat('(', cap_terms, ')')
     AND blob RLIKE '(may|might|sometimes|occasionally|limited|basic|general|planned|proposed|upcoming|if available|on request|referral only)'
    THEN 1 ELSE 0
  END AS vague_language
FROM (
  SELECT
    fc.facility_id,
    cu.capability_type,
    concat_ws(' ', fc.description, fc.capability, fc.procedure) AS blob,
    CASE cu.capability_type
      WHEN 'emergency_maternity' THEN 'maternity|obstetric|obstetrics|emergency obstetric|labour|delivery|cemonc|bemonc'
      WHEN 'icu'      THEN 'icu|intensive care|critical care'
      WHEN 'dialysis' THEN 'dialysis|haemodialysis|hemodialysis|renal replacement'
      WHEN 'trauma'   THEN 'trauma|emergency|casualty|accident'
      WHEN 'oncology' THEN 'oncology|cancer|tumour|tumor'
      WHEN 'nicu'     THEN 'nicu|neonatal intensive care|newborn care|sncu'
    END AS cap_terms
  FROM caregap.facility_clean fc
  CROSS JOIN capability_universe cu
) fc;

-- COMMAND ----------

-- Assemble all flags, then apply the exact weighted formula and labels.
CREATE OR REPLACE TABLE caregap.facility_scores AS
WITH flags AS (
  SELECT
    c.facility_id,
    c.capability_type,
    c.capability_match,
    c.procedure_match,
    c.equipment_match,
    c.specialty_match,
    c.description_match,
    -- source_url_present: WEIGHTS.source_url (+5)
    CASE WHEN c.source_urls IS NOT NULL AND trim(c.source_urls) <> '' THEN 1 ELSE 0 END AS source_url_present,
    -- contradiction: negation OR (capability claimed but no procedure AND no equipment)
    CASE
      WHEN coalesce(n.negation_contradiction, 0) = 1 THEN 1
      WHEN c.capability_match = 1 AND c.procedure_match = 0 AND c.equipment_match = 0 THEN 1
      ELSE 0
    END AS contradiction_flag,
    coalesce(v.vague_language, 0) AS vague_language,
    -- missing_critical: capability claimed AND a critical field (procedure/equipment) blank
    CASE
      WHEN c.capability_match = 1
       AND ( c.procedure IS NULL OR trim(c.procedure) = ''
          OR c.equipment IS NULL OR trim(c.equipment) = '' )
      THEN 1 ELSE 0
    END AS missing_critical,
    -- list the blank critical fields for the explanation / missing_fields column
    concat_ws(',',
      CASE WHEN c.procedure IS NULL OR trim(c.procedure) = '' THEN 'procedure' END,
      CASE WHEN c.equipment IS NULL OR trim(c.equipment) = '' THEN 'equipment' END
    ) AS missing_fields
  FROM facility_components c
  LEFT JOIN facility_negation n
    ON n.facility_id = c.facility_id AND n.capability_type = c.capability_type
  LEFT JOIN facility_vague v
    ON v.facility_id = c.facility_id AND v.capability_type = c.capability_type
),
scored AS (
  SELECT
    facility_id,
    capability_type,
    contradiction_flag,
    missing_fields,
    -- exact weighted sum, clamped 0..100
    greatest(0, least(100,
        25 * capability_match
      + 20 * procedure_match
      + 20 * equipment_match
      + 15 * specialty_match
      + 15 * description_match
      +  5 * source_url_present
      - 20 * contradiction_flag
      - 10 * vague_language
      - 10 * missing_critical
    )) AS trust_score,
    capability_match, procedure_match, equipment_match,
    specialty_match, description_match, source_url_present,
    vague_language, missing_critical
  FROM flags
)
SELECT
  facility_id,
  capability_type,
  trust_score,
  -- contradiction overrides the score band (src/scoring.py)
  CASE
    WHEN contradiction_flag = 1 THEN 'Contradictory evidence'
    WHEN trust_score BETWEEN 80 AND 100 THEN 'Strong evidence'
    WHEN trust_score BETWEEN 55 AND 79  THEN 'Partial evidence'
    WHEN trust_score BETWEEN 30 AND 54  THEN 'Weak evidence'
    WHEN trust_score BETWEEN 1  AND 29  THEN 'Very weak evidence'
    ELSE 'No usable evidence'
  END AS trust_label,
  CAST(contradiction_flag AS BOOLEAN) AS contradiction_flag,
  missing_fields,
  -- compact, human-readable explanation echoing src/scoring.py::_explain
  concat_ws(' | ',
    concat('matches[cap=', capability_match, ',proc=', procedure_match,
           ',equip=', equipment_match, ',spec=', specialty_match,
           ',desc=', description_match, ']'),
    CASE WHEN source_url_present = 1 THEN 'source URL present' END,
    CASE WHEN contradiction_flag = 1 THEN 'CONTRADICTION: claim lacks procedure/equipment support or is negated' END,
    CASE WHEN vague_language = 1 THEN 'hedged/vague language' END,
    CASE WHEN missing_critical = 1 AND missing_fields <> '' THEN concat('missing critical field(s): ', missing_fields) END
  ) AS explanation
FROM scored;

-- COMMAND ----------

-- Referral candidates: evidenced facilities (Strong / Partial) with coordinates,
-- ready for the routing tab. Highest trust first.
CREATE OR REPLACE TABLE caregap.referral_candidates AS
SELECT
  s.facility_id,
  s.capability_type,
  s.trust_label,
  s.trust_score,
  fc.latitude,
  fc.longitude
FROM caregap.facility_scores s
JOIN caregap.facility_clean fc ON fc.facility_id = s.facility_id
WHERE s.trust_label IN ('Strong evidence', 'Partial evidence')
ORDER BY s.capability_type, s.trust_score DESC;

-- COMMAND ----------

-- Sanity checks.
SELECT capability_type, trust_label, count(*) AS n
FROM caregap.facility_scores
GROUP BY capability_type, trust_label
ORDER BY capability_type, trust_label;

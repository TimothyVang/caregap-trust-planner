-- Databricks notebook source
-- ============================================================================
-- 02_extract_claims — populate facility_claims and facility_evidence
-- ============================================================================
-- Scan the cleaned facility text (caregap.facility_clean from notebook 01) for
-- capability keywords and record one evidence row per (facility, capability,
-- field, keyword) hit. This mirrors src/evidence.py:
--   * matched_keywords() — case-insensitive substring match (text already
--     lower/trimmed in facility_clean).
--   * FIELD_FOR_COMPONENT — which field each component reads:
--       capability  -> capability field   (capability keyword set)
--       procedure   -> procedure field    (procedure keyword set)
--       equipment   -> equipment field    (equipment keyword set)
--       specialty   -> specialties field  (specialty keyword set)
--       description -> description field  (capability keyword set)
--
-- Capability keyword lists below are copied verbatim from
-- src/capabilities.py::CAPABILITIES so SQL and Python agree.
-- ============================================================================

-- COMMAND ----------

USE caregap;

-- COMMAND ----------

-- Reference table: one row per (capability_type, field, component, keyword).
-- "field" is the facility column scanned; "component" is the scoring component.
-- e.g. NICU equipment keywords: incubator, neonatal ventilator, radiant warmer,
-- phototherapy unit, cpap.
CREATE OR REPLACE TEMP VIEW capability_keywords AS
SELECT * FROM VALUES
  -- ---- emergency_maternity ----
  ('emergency_maternity','capability','capability','maternity'),
  ('emergency_maternity','capability','capability','obstetric'),
  ('emergency_maternity','capability','capability','obstetrics'),
  ('emergency_maternity','capability','capability','emergency obstetric'),
  ('emergency_maternity','capability','capability','labour'),
  ('emergency_maternity','capability','capability','delivery'),
  ('emergency_maternity','capability','capability','cemonc'),
  ('emergency_maternity','capability','capability','bemonc'),
  ('emergency_maternity','procedure','procedure','caesarean'),
  ('emergency_maternity','procedure','procedure','c-section'),
  ('emergency_maternity','procedure','procedure','cesarean'),
  ('emergency_maternity','procedure','procedure','assisted delivery'),
  ('emergency_maternity','procedure','procedure','emergency delivery'),
  ('emergency_maternity','procedure','procedure','obstetric surgery'),
  ('emergency_maternity','equipment','equipment','labour table'),
  ('emergency_maternity','equipment','equipment','delivery kit'),
  ('emergency_maternity','equipment','equipment','neonatal resuscitation'),
  ('emergency_maternity','equipment','equipment','fetal monitor'),
  ('emergency_maternity','equipment','equipment','operation theatre'),
  ('emergency_maternity','specialties','specialty','obstetrics'),
  ('emergency_maternity','specialties','specialty','gynaecology'),
  ('emergency_maternity','specialties','specialty','gynecology'),
  ('emergency_maternity','specialties','specialty','obstetrician'),
  ('emergency_maternity','description','capability','maternity'),
  ('emergency_maternity','description','capability','obstetric'),
  ('emergency_maternity','description','capability','obstetrics'),
  ('emergency_maternity','description','capability','emergency obstetric'),
  ('emergency_maternity','description','capability','labour'),
  ('emergency_maternity','description','capability','delivery'),
  ('emergency_maternity','description','capability','cemonc'),
  ('emergency_maternity','description','capability','bemonc'),
  -- ---- icu ----
  ('icu','capability','capability','icu'),
  ('icu','capability','capability','intensive care'),
  ('icu','capability','capability','critical care'),
  ('icu','procedure','procedure','mechanical ventilation'),
  ('icu','procedure','procedure','intubation'),
  ('icu','procedure','procedure','central line'),
  ('icu','procedure','procedure','critical care monitoring'),
  ('icu','equipment','equipment','ventilator'),
  ('icu','equipment','equipment','icu bed'),
  ('icu','equipment','equipment','multipara monitor'),
  ('icu','equipment','equipment','infusion pump'),
  ('icu','equipment','equipment','defibrillator'),
  ('icu','specialties','specialty','intensivist'),
  ('icu','specialties','specialty','critical care'),
  ('icu','specialties','specialty','anaesthesia'),
  ('icu','specialties','specialty','anesthesia'),
  ('icu','description','capability','icu'),
  ('icu','description','capability','intensive care'),
  ('icu','description','capability','critical care'),
  -- ---- dialysis ----
  ('dialysis','capability','capability','dialysis'),
  ('dialysis','capability','capability','haemodialysis'),
  ('dialysis','capability','capability','hemodialysis'),
  ('dialysis','capability','capability','renal replacement'),
  ('dialysis','procedure','procedure','haemodialysis'),
  ('dialysis','procedure','procedure','hemodialysis'),
  ('dialysis','procedure','procedure','peritoneal dialysis'),
  ('dialysis','procedure','procedure','av fistula'),
  ('dialysis','equipment','equipment','dialysis machine'),
  ('dialysis','equipment','equipment','dialyzer'),
  ('dialysis','equipment','equipment','ro plant'),
  ('dialysis','equipment','equipment','reverse osmosis'),
  ('dialysis','specialties','specialty','nephrology'),
  ('dialysis','specialties','specialty','nephrologist'),
  ('dialysis','description','capability','dialysis'),
  ('dialysis','description','capability','haemodialysis'),
  ('dialysis','description','capability','hemodialysis'),
  ('dialysis','description','capability','renal replacement'),
  -- ---- trauma ----
  ('trauma','capability','capability','trauma'),
  ('trauma','capability','capability','emergency'),
  ('trauma','capability','capability','casualty'),
  ('trauma','capability','capability','accident'),
  ('trauma','procedure','procedure','trauma surgery'),
  ('trauma','procedure','procedure','fracture fixation'),
  ('trauma','procedure','procedure','emergency laparotomy'),
  ('trauma','procedure','procedure','wound debridement'),
  ('trauma','equipment','equipment','ct scan'),
  ('trauma','equipment','equipment','x-ray'),
  ('trauma','equipment','equipment','operation theatre'),
  ('trauma','equipment','equipment','blood bank'),
  ('trauma','equipment','equipment','ambulance'),
  ('trauma','specialties','specialty','orthopaedics'),
  ('trauma','specialties','specialty','orthopedics'),
  ('trauma','specialties','specialty','general surgery'),
  ('trauma','specialties','specialty','emergency medicine'),
  ('trauma','description','capability','trauma'),
  ('trauma','description','capability','emergency'),
  ('trauma','description','capability','casualty'),
  ('trauma','description','capability','accident'),
  -- ---- oncology ----
  ('oncology','capability','capability','oncology'),
  ('oncology','capability','capability','cancer'),
  ('oncology','capability','capability','tumour'),
  ('oncology','capability','capability','tumor'),
  ('oncology','procedure','procedure','chemotherapy'),
  ('oncology','procedure','procedure','radiotherapy'),
  ('oncology','procedure','procedure','tumour resection'),
  ('oncology','procedure','procedure','biopsy'),
  ('oncology','equipment','equipment','linear accelerator'),
  ('oncology','equipment','equipment','linac'),
  ('oncology','equipment','equipment','chemo daycare'),
  ('oncology','equipment','equipment','pet ct'),
  ('oncology','specialties','specialty','oncology'),
  ('oncology','specialties','specialty','oncologist'),
  ('oncology','specialties','specialty','haematology'),
  ('oncology','specialties','specialty','radiation oncology'),
  ('oncology','description','capability','oncology'),
  ('oncology','description','capability','cancer'),
  ('oncology','description','capability','tumour'),
  ('oncology','description','capability','tumor'),
  -- ---- nicu ----
  ('nicu','capability','capability','nicu'),
  ('nicu','capability','capability','neonatal intensive care'),
  ('nicu','capability','capability','newborn care'),
  ('nicu','capability','capability','sncu'),
  ('nicu','procedure','procedure','neonatal ventilation'),
  ('nicu','procedure','procedure','surfactant'),
  ('nicu','procedure','procedure','phototherapy'),
  ('nicu','procedure','procedure','neonatal resuscitation'),
  ('nicu','equipment','equipment','incubator'),
  ('nicu','equipment','equipment','neonatal ventilator'),
  ('nicu','equipment','equipment','radiant warmer'),
  ('nicu','equipment','equipment','phototherapy unit'),
  ('nicu','equipment','equipment','cpap'),
  ('nicu','specialties','specialty','neonatology'),
  ('nicu','specialties','specialty','paediatrics'),
  ('nicu','specialties','specialty','pediatrics'),
  ('nicu','specialties','specialty','neonatologist'),
  ('nicu','description','capability','nicu'),
  ('nicu','description','capability','neonatal intensive care'),
  ('nicu','description','capability','newborn care'),
  ('nicu','description','capability','sncu')
AS t(capability_type, field, component, keyword);

-- COMMAND ----------

-- Long-form facility text: one row per (facility, field) with the cleaned blob.
-- "field" names line up with capability_keywords.field so we can join+LIKE.
CREATE OR REPLACE TEMP VIEW facility_field_text AS
SELECT facility_id, 'capability'  AS field, capability  AS field_text FROM caregap.facility_clean
UNION ALL
SELECT facility_id, 'procedure'   AS field, procedure   AS field_text FROM caregap.facility_clean
UNION ALL
SELECT facility_id, 'equipment'   AS field, equipment   AS field_text FROM caregap.facility_clean
UNION ALL
SELECT facility_id, 'specialties' AS field, specialties AS field_text FROM caregap.facility_clean
UNION ALL
SELECT facility_id, 'description' AS field, description AS field_text FROM caregap.facility_clean;

-- COMMAND ----------

-- Evidence = every keyword that appears (case-insensitive substring) in its
-- field. Equivalent to: array_contains(matched_keywords(field_text, kws), kw).
-- We use LIKE on the already-normalized (lower/trim) text from facility_clean.
CREATE OR REPLACE TABLE caregap.facility_evidence AS
SELECT
  md5(concat_ws('|', f.facility_id, k.capability_type, k.field, k.keyword)) AS evidence_id,
  f.facility_id,
  k.capability_type,
  k.field,
  k.keyword,
  -- snippet: short window of original text around the match (best-effort).
  substr(
    f.field_text,
    greatest(1, CAST(locate(k.keyword, f.field_text) AS INT) - 30),
    length(k.keyword) + 60
  ) AS snippet
FROM facility_field_text f
JOIN capability_keywords k
  ON f.field = k.field
 AND f.field_text LIKE concat('%', k.keyword, '%')
WHERE f.field_text IS NOT NULL AND f.field_text <> '';

-- COMMAND ----------

-- Claims = one row per evidence hit, with provenance metadata. Same grain as
-- facility_evidence but framed as asserted claims for the audit / "show work" UI.
CREATE OR REPLACE TABLE caregap.facility_claims AS
SELECT
  md5(concat_ws('|', e.facility_id, e.capability_type, e.field, e.keyword)) AS claim_id,
  e.facility_id,
  e.capability_type,
  e.keyword               AS claim_text,
  e.field                 AS claim_source_field,
  e.snippet               AS extracted_evidence_span,
  'keyword_match'         AS extraction_method,
  current_timestamp()     AS created_at
FROM caregap.facility_evidence e;

-- COMMAND ----------

-- Sanity checks.
SELECT capability_type, count(*) AS evidence_hits
FROM caregap.facility_evidence
GROUP BY capability_type
ORDER BY capability_type;

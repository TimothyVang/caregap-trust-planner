# CareGap Trust Planner

CareGap Trust Planner helps healthcare planners distinguish real care gaps from data uncertainty using evidence-backed facility trust scores, regional planning confidence, referral shortlists, and human review workflows. Built for the Databricks Apps & Agents for Good Hackathon 2026.

## The one idea

> We do not turn weak data into confident recommendations. We turn weak data into visible uncertainty and human review.

A blank spot on the map may be a data desert, not a medical desert. The absence of evidence about a facility is not evidence that care is unavailable, and the planner sees that distinction explicitly rather than having it hidden inside a single confident number.

## Features

- **Plan Care Gaps** — Surfaces regions that look underserved and separates likely medical deserts from regions where the data is simply too thin to judge, with a planning confidence score for each region.
- **Refer Patient** — Ranks referral candidates for a given need by evidence-backed facility trust, showing the citations and missing fields behind every ranking instead of a bare score.
- **Review Data** — Prioritizes suspicious or contradictory records for human review, lets planners override claims with notes, and persists those decisions back to app state.

## Quickstart (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python data/generate_synthetic.py     # writes data/facilities_sample.csv
streamlit run app.py
```

Note: locally it uses a synthetic dataset and SQLite; in Databricks it uses the real dataset + Lakebase.

## Architecture

The Databricks App (Streamlit) renders the UI and persists planner actions — saved shortlists, review decisions, and planning scenarios — to Lakebase (Postgres). Heavy scoring is precomputed in Databricks SQL/Delta tables (`facility_scores`, `regional_gap_scores`) so the app compute stays light and only reads results and writes user actions.

See [docs/architecture.md](docs/architecture.md) and [docs/scoring_methodology.md](docs/scoring_methodology.md).

## Repository structure

```text
caregap-trust-planner/
├── README.md
├── LICENSE
├── app.py
├── app.yaml
├── requirements.txt
├── src/
│   ├── scoring.py
│   ├── evidence.py
│   ├── geo.py
│   ├── db.py
│   ├── data_loader.py
│   └── capabilities.py
├── sql/
│   ├── lakebase_schema.sql
│   └── databricks_tables.sql
├── notebooks/
│   ├── 01_ingest_dataset.sql
│   ├── 02_extract_capabilities.sql
│   ├── 03_score_facilities.sql
│   └── 04_score_regions.sql
├── data/
│   ├── generate_synthetic.py
│   └── facilities_sample.csv
├── docs/
└── assets/
```

## Scoring (at a glance)

```text
trust_score = 25*capability
            + 20*procedure
            + 20*equipment
            + 15*specialty
            + 15*description
            +  5*source_url
            - 20*contradiction
            - 10*vague
            - 10*missing_critical
```

Scores map to labels: **Strong**, **Partial**, **Weak**, **Very weak**, and **No usable** evidence, plus a separate **Contradictory** flag for records whose claims conflict with each other.

## Databricks deployment

- Precompute `facility_scores` and `regional_gap_scores` in Databricks SQL/Delta.
- Deploy the app via Databricks Apps using the `app.yaml` entry point.
- Bind Lakebase for persisted user actions (`saved_shortlists`, `review_decisions`, and related tables).
- Keep app files under 10 MB — do not ship the dataset with the app.

## Judging Alignment

### Business Applicability

CareGap Trust Planner helps healthcare planners and NGO coordinators make safer decisions from messy facility data. Instead of trusting a clean-looking dashboard built on incomplete records, planners get trust labels, confidence scores, and review workflows that keep human judgment in the loop where the data is weakest.

### Data Relevance

The app uses the provided 10,000-record healthcare facility dataset and runs as a Databricks App, backed by Lakebase for application state and Databricks SQL for analytics. The dataset drives every facility trust score, regional gap score, and referral shortlist the planner sees.

### Creativity

The core insight is that missing data is not missing care. CareGap Trust Planner separates medical deserts from data deserts instead of treating absent records as absent services, so planners are not pushed toward false confidence about regions that are simply under-documented.

### Thoroughness

Every recommendation carries its evidence. Each facility ranking shows the supporting text snippets, the fields that are missing, the trust label, and the uncertainty around the score, so a planner can audit why a facility ranked where it did rather than accepting an opaque number.

### Well-Architected

Facility and regional scores are precomputed in Databricks SQL/Delta tables, and the app compute only renders the UI and persists user actions to Lakebase. This keeps the interactive layer responsive and inexpensive while the heavy analytics live where they belong.

## Limitations

CareGap Trust Planner is decision support, not medical advice. Sparse data about a region or facility is not proof that care is unavailable, and every recommendation is intended for human verification before it informs a real planning decision. See [docs/limitations.md](docs/limitations.md).

## License

Apache-2.0.

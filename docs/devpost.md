# Devpost Submission Cheat-Sheet — CareGap Trust Planner

Paste-ready content for every Devpost field. Built for the Databricks Apps & Agents for Good Hackathon 2026.

## Project name

CareGap Trust Planner

## Elevator pitch (<= 200 chars)

Evidence-backed Databricks App that separates medical deserts from data deserts and helps planners rank referral options with citations and uncertainty.

## About the project

### Inspiration

A blank spot on a coverage map looks like a region with no care, but often it is just a region with no data. We kept seeing tools that turned incomplete facility records into confident recommendations, quietly hiding uncertainty inside a single score. CareGap Trust Planner was built to do the opposite — to make weak data visible and route it to human review instead of dressing it up as certainty.

### What it does

CareGap Trust Planner gives healthcare planners a set of evidence-first tools:

- Identify likely care deserts from regional patterns in the facility data.
- Distinguish them from data-poor regions where the records are too thin to judge.
- Rank referral candidates by evidence-backed trust for a specific need.
- Inspect citations — the actual facility text behind each ranking.
- Save shortlists and planning scenarios for later comparison.
- Override suspicious claims with notes when a record looks wrong.
- Prioritize records for human review when data is contradictory or missing.

### How we built it

The interface is a Streamlit app built to run as a Databricks App. The scoring — facility trust scores and regional gap scores — is dataset-agnostic: the public repo runs it in-process over a representative synthetic sample so it works without a workspace, and notebooks 01-04 port the same logic to Databricks SQL/Delta for the provided 10,000-record dataset. Lakebase (Postgres) is the target store for application state (saved shortlists, review decisions, planning scenarios); the local build uses an identical SQLite schema. Either way the app compute only renders the UI and persists planner actions, keeping it light and fast.

### What makes it different

Most tools treat missing data as missing care. CareGap Trust Planner treats them as different problems. It scores how trustworthy the evidence behind each facility is, labels regions by planning confidence, and surfaces the citations and missing fields behind every recommendation — so planners can audit the reasoning instead of trusting an opaque number.

### Limitations

This is decision support, not medical advice. Sparse data about a region is not proof that care is unavailable, and synthetic data is used in the local build. Every recommendation is meant for human verification before it informs a real planning decision.

## Built with (tags)

Databricks Apps, Lakebase, Databricks SQL, Databricks Free Edition, Python, Streamlit, PostgreSQL, Healthcare, Geospatial Analysis, Data Quality

## Try it out

- GitHub repo: https://github.com/TimothyVang/caregap-trust-planner
- Databricks App URL: <placeholder — paste deployed Databricks App URL here>

## Testing instructions

Run locally with the Quickstart steps:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python data/generate_synthetic.py     # writes data/facilities_sample.csv
streamlit run app.py
```

Then demo the three cases:

1. **Mumbai strong referral** — a well-documented facility that ranks highly with supporting citations.
2. **Gadchiroli data desert** — a region that looks empty but is flagged as data-poor rather than care-poor.
3. **Sunrise suspicious claim** — a record with a contradictory or implausible claim that gets routed to human review and can be overridden with a note.

## Known limitations

- Decision support, not medical advice.
- Sparse data handling: absence of evidence is not evidence of absent care.
- The local build uses synthetic data and SQLite; Databricks uses the real dataset and Lakebase.

## Compliance checklist

- [ ] App runs as a Databricks App.
- [ ] Uses the provided 10,000-record healthcare facility dataset.
- [ ] Uses Lakebase for persisted user actions.
- [ ] Uses at least one additional Databricks tool (Databricks SQL/Delta).
- [ ] Public GitHub repo.
- [ ] Open-source license (Apache-2.0).
- [ ] Commit history within the project period.
- [ ] Demo video is public and under 3 minutes.
- [ ] All Devpost fields filled in.
- [ ] Thumbnail provided.
- [ ] Built-with tags added.
- [ ] Known limitations documented.

"""Generate a small, deterministic synthetic facility dataset.

This stands in for the real 10,000-record Databricks healthcare dataset so the
app runs end-to-end locally. It is intentionally seeded to exercise the three
demo cases:

  1. Strong referral   -> dense Mumbai facilities with real evidence
  2. Data desert       -> sparse Gadchiroli district, mostly empty records
  3. Suspicious claim  -> facility claims NICU/ICU with no procedure/equipment

Schema matches facility_raw in docs/architecture.md.
Run:  python data/generate_synthetic.py
"""

from __future__ import annotations

import csv
from pathlib import Path

COLUMNS = [
    "facility_id", "name", "address", "state", "district", "latitude", "longitude",
    "description", "capability", "procedure", "equipment", "specialties",
    "source_urls", "numberDoctors", "capacity", "yearEstablished",
]


def F(**kw) -> dict:
    row = {c: "" for c in COLUMNS}
    row.update(kw)
    return row


ROWS = [
    # ---- Group A: Mumbai, Maharashtra — dense, well-evidenced ----
    F(facility_id="MH-MUM-001", name="KEM Hospital", address="Acharya Donde Marg, Parel",
      state="Maharashtra", district="Mumbai", latitude=19.0040, longitude=72.8420,
      description="Tertiary care hospital providing 24x7 emergency obstetric and maternity services.",
      capability="emergency obstetric; maternity; ICU; trauma",
      procedure="caesarean; assisted delivery; emergency laparotomy; mechanical ventilation",
      equipment="operation theatre; fetal monitor; neonatal resuscitation; ventilator; icu bed; ct scan",
      specialties="obstetrics; gynaecology; general surgery; intensivist",
      source_urls="https://kem.example.org", numberDoctors=140, capacity=1800, yearEstablished=1926),
    F(facility_id="MH-MUM-002", name="Sion Hospital", address="Sion West",
      state="Maharashtra", district="Mumbai", latitude=19.0430, longitude=72.8620,
      description="Government hospital with critical care and emergency maternity units.",
      capability="ICU; emergency obstetric; maternity",
      procedure="mechanical ventilation; intubation; caesarean",
      equipment="ventilator; icu bed; multipara monitor; labour table",
      specialties="critical care; obstetrics; anaesthesia",
      source_urls="https://sion.example.org", numberDoctors=95, capacity=1400, yearEstablished=1947),
    F(facility_id="MH-MUM-003", name="Wadia Maternity Hospital", address="Parel",
      state="Maharashtra", district="Mumbai", latitude=19.0010, longitude=72.8410,
      description="Dedicated maternity and neonatal hospital.",
      capability="emergency obstetric; maternity; NICU",
      procedure="caesarean; neonatal resuscitation; surfactant",
      equipment="incubator; radiant warmer; neonatal ventilator; fetal monitor",
      specialties="obstetrics; neonatology; paediatrics",
      source_urls="https://wadia.example.org", numberDoctors=70, capacity=400, yearEstablished=1926),
    F(facility_id="MH-MUM-004", name="Lilavati Hospital", address="Bandra West",
      state="Maharashtra", district="Mumbai", latitude=19.0510, longitude=72.8290,
      description="Multispeciality private hospital with oncology and dialysis units.",
      capability="oncology; dialysis; ICU",
      procedure="chemotherapy; haemodialysis; mechanical ventilation",
      equipment="linear accelerator; dialysis machine; ventilator; icu bed",
      specialties="oncology; nephrology; critical care",
      source_urls="https://lilavati.example.org", numberDoctors=110, capacity=320, yearEstablished=1997),
    F(facility_id="MH-MUM-005", name="Rajawadi Hospital", address="Ghatkopar East",
      state="Maharashtra", district="Mumbai", latitude=19.0860, longitude=72.9080,
      description="Suburban hospital offering maternity services.",
      capability="maternity; emergency obstetric",
      procedure="assisted delivery",
      equipment="labour table",
      specialties="obstetrics",
      source_urls="", numberDoctors=30, capacity=300, yearEstablished=1978),
    F(facility_id="MH-MUM-006", name="Hinduja Clinic Khar", address="Khar West",
      state="Maharashtra", district="Mumbai", latitude=19.0700, longitude=72.8380,
      description="Day clinic; dialysis available on request, limited hours.",
      capability="dialysis",
      procedure="haemodialysis",
      equipment="dialysis machine",
      specialties="nephrology",
      source_urls="https://hinduja-khar.example.org", numberDoctors=12, capacity=20, yearEstablished=2012),

    # ---- Group B: Gadchiroli, Maharashtra — sparse / data-poor ----
    F(facility_id="MH-GAD-001", name="Gadchiroli District Hospital", address="Gadchiroli",
      state="Maharashtra", district="Gadchiroli", latitude=20.1800, longitude=80.0030,
      description="District hospital.",
      capability="general; maternity",
      procedure="", equipment="", specialties="", source_urls="",
      numberDoctors=8, capacity=200, yearEstablished=1985),
    F(facility_id="MH-GAD-002", name="Aheri Rural Hospital", address="Aheri",
      state="Maharashtra", district="Gadchiroli", latitude=19.4200, longitude=80.0000,
      description="Rural hospital.",
      capability="", procedure="", equipment="", specialties="", source_urls="",
      numberDoctors=3, capacity=50, yearEstablished=1990),
    F(facility_id="MH-GAD-003", name="Bhamragad PHC", address="Bhamragad",
      state="Maharashtra", district="Gadchiroli", latitude=19.3000, longitude=80.4000,
      description="Primary health centre, basic services only.",
      capability="general",
      procedure="", equipment="", specialties="", source_urls="",
      numberDoctors=2, capacity=10, yearEstablished=2001),
    F(facility_id="MH-GAD-004", name="Etapalli Sub-centre", address="Etapalli",
      state="Maharashtra", district="Gadchiroli", latitude=19.6800, longitude=80.2300,
      description="",
      capability="", procedure="", equipment="", specialties="", source_urls="",
      numberDoctors=1, capacity=6, yearEstablished=2005),

    # ---- Group C: suspicious / contradictory claims (Pune) ----
    F(facility_id="MH-PUN-001", name="Sunrise Multispeciality", address="Hadapsar, Pune",
      state="Maharashtra", district="Pune", latitude=18.5000, longitude=73.9400,
      description="Advanced NICU and ICU facility available.",  # claims, but no support below
      capability="NICU; ICU; oncology",
      procedure="", equipment="", specialties="",
      source_urls="https://sunrise.example.org",
      numberDoctors=15, capacity=80, yearEstablished=2015),
    F(facility_id="MH-PUN-002", name="Greenfield Care Centre", address="Kothrud, Pune",
      state="Maharashtra", district="Pune", latitude=18.5070, longitude=73.8070,
      description="ICU not functional currently; maternity ward operational.",  # explicit negation
      capability="ICU; maternity",
      procedure="assisted delivery",
      equipment="labour table",
      specialties="obstetrics",
      source_urls="", numberDoctors=18, capacity=120, yearEstablished=2010),
    F(facility_id="MH-PUN-003", name="Ruby Hall Clinic", address="Sassoon Road, Pune",
      state="Maharashtra", district="Pune", latitude=18.5360, longitude=73.8770,
      description="Tertiary hospital with trauma and oncology services.",
      capability="trauma; oncology; ICU",
      procedure="trauma surgery; chemotherapy; mechanical ventilation",
      equipment="ct scan; operation theatre; ventilator; chemo daycare",
      specialties="orthopaedics; oncology; critical care",
      source_urls="https://rubyhall.example.org", numberDoctors=130, capacity=750, yearEstablished=1959),

    # ---- Group D: Patna, Bihar — mixed evidence ----
    F(facility_id="BR-PAT-001", name="PMCH Patna", address="Ashok Rajpath, Patna",
      state="Bihar", district="Patna", latitude=25.6210, longitude=85.1780,
      description="Large government medical college hospital with maternity and trauma care.",
      capability="emergency obstetric; trauma; ICU",
      procedure="caesarean; trauma surgery; mechanical ventilation",
      equipment="operation theatre; ventilator; ct scan",
      specialties="obstetrics; general surgery; critical care",
      source_urls="https://pmch.example.org", numberDoctors=85, capacity=1700, yearEstablished=1925),
    F(facility_id="BR-PAT-002", name="Patna Sadar Hospital", address="Patna",
      state="Bihar", district="Patna", latitude=25.6000, longitude=85.1400,
      description="Sadar hospital; maternity services, sometimes limited staff.",
      capability="maternity; emergency obstetric",
      procedure="assisted delivery",
      equipment="labour table",
      specialties="obstetrics",
      source_urls="", numberDoctors=20, capacity=250, yearEstablished=1972),
    F(facility_id="BR-PAT-003", name="Kidney Care Patna", address="Kankarbagh, Patna",
      state="Bihar", district="Patna", latitude=25.5900, longitude=85.1600,
      description="Dialysis centre.",
      capability="dialysis",
      procedure="haemodialysis",
      equipment="dialysis machine; reverse osmosis",
      specialties="nephrology",
      source_urls="https://kidneycare.example.org", numberDoctors=9, capacity=30, yearEstablished=2016),

    # ---- Group E: Malkangiri, Odisha — sparse + one contradictory ----
    F(facility_id="OD-MAL-001", name="Malkangiri DHH", address="Malkangiri",
      state="Odisha", district="Malkangiri", latitude=18.3600, longitude=81.8800,
      description="District headquarters hospital.",
      capability="maternity; NICU",  # claims NICU, nothing supports it
      procedure="", equipment="", specialties="", source_urls="",
      numberDoctors=6, capacity=180, yearEstablished=1992),
    F(facility_id="OD-MAL-002", name="Kalimela CHC", address="Kalimela",
      state="Odisha", district="Malkangiri", latitude=18.0200, longitude=81.9000,
      description="Community health centre.",
      capability="general",
      procedure="", equipment="", specialties="", source_urls="",
      numberDoctors=2, capacity=30, yearEstablished=2003),

    # ---- Group F: Jaipur, Rajasthan — good oncology/dialysis ----
    F(facility_id="RJ-JAI-001", name="SMS Hospital", address="JLN Marg, Jaipur",
      state="Rajasthan", district="Jaipur", latitude=26.8970, longitude=75.8140,
      description="Major government hospital with oncology, dialysis and ICU.",
      capability="oncology; dialysis; ICU; trauma",
      procedure="chemotherapy; haemodialysis; mechanical ventilation; trauma surgery",
      equipment="linear accelerator; dialysis machine; ventilator; ct scan",
      specialties="oncology; nephrology; critical care; orthopaedics",
      source_urls="https://sms.example.org", numberDoctors=160, capacity=2300, yearEstablished=1959),
    F(facility_id="RJ-JAI-002", name="Jaipur Maternity Home", address="Jaipur",
      state="Rajasthan", district="Jaipur", latitude=26.9120, longitude=75.7870,
      description="Maternity home with neonatal care.",
      capability="maternity; emergency obstetric; NICU",
      procedure="caesarean; neonatal resuscitation",
      equipment="incubator; radiant warmer; fetal monitor",
      specialties="obstetrics; neonatology",
      source_urls="https://jaipurmat.example.org", numberDoctors=28, capacity=160, yearEstablished=2008),
]


def main() -> Path:
    out = Path(__file__).resolve().parent / "facilities_sample.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(ROWS)
    print(f"Wrote {len(ROWS)} facilities -> {out}")
    return out


if __name__ == "__main__":
    main()

"""One-off: generate a FIRST-PASS short-label table for the 252 OpenAlex subfields.

Pulls the canonical subfield list from OpenAlex and applies a word-abbreviation pass, writing
docs/subfield_abbreviations.md (sid | name | short). The `short` column feeds the Explore "FIELD"
column (the synthetic-field blend), targeting ~<=18 chars. After this runs once, the .md is the
hand-edited source of truth — don't blindly re-run it (it would overwrite edits).

Run: python pipeline/gen_subfield_abbrev.py
"""
import os
import _env
_env.load_env()
import requests

MAILTO = os.environ.get("OPENALEX_MAILTO", "ktulrich@gmail.com")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "subfield_abbreviations.md")

# Whole-phrase overrides win first (the long / department-relevant ones).
PHRASE = {
    "Management Science and Operations Research": "Mgmt Sci & OR",
    "Information Systems and Management": "Info Sys & Mgmt",
    "General Decision Sciences": "Decision Sci",
    "Management Information Systems": "Mgmt Info Sys",
    "Management of Technology and Innovation": "Tech & Innovation",
    "Strategy and Management": "Strategy & Mgmt",
    "Organizational Behavior and Human Resource Management": "Org Behavior & HR",
    "Business and International Management": "Business & Intl Mgmt",
    "Tourism, Leisure and Hospitality Management": "Tourism & Hospitality",
    "Economics and Econometrics": "Economics",
    "General Economics, Econometrics and Finance": "Gen Economics",
    "Sociology and Political Science": "Sociology & PoliSci",
    "Political Science and International Relations": "PoliSci & Intl Rel",
    "Experimental and Cognitive Psychology": "Exp & Cognitive Psych",
    "Developmental and Educational Psychology": "Dev & Educ Psych",
    "Neuropsychology and Physiological Psychology": "Neuro & Physiol Psych",
    "Emergency Medical Services": "Emergency Med Svcs",
    "General Health Professions": "Health Professions",
    "Statistics, Probability and Uncertainty": "Stats, Prob & Uncert",
    "Statistics and Probability": "Stats & Prob",
    "Computer Networks and Communications": "Networks & Comms",
    "Computational Theory and Mathematics": "Comp Theory & Math",
    "Computer Vision and Pattern Recognition": "Computer Vision",
    "Computer Science Applications": "CS Applications",
    "Artificial Intelligence": "AI",
    "Human-Computer Interaction": "HCI",
    "Hardware and Architecture": "Hardware & Arch",
    "Library and Information Sciences": "Library & Info Sci",
    "Safety, Risk, Reliability and Quality": "Safety & Risk",
    "Industrial and Manufacturing Engineering": "Indust & Mfg Eng",
    "Electrical and Electronic Engineering": "Electrical Eng",
    "Control and Systems Engineering": "Control & Sys Eng",
    "Civil and Structural Engineering": "Civil Eng",
    "Building and Construction": "Building & Constr",
    "Ecology, Evolution, Behavior and Systematics": "Ecology & Evolution",
    "Public Health, Environmental and Occupational Health": "Public & Environ Health",
    "Health, Toxicology and Mutagenesis": "Health & Toxicology",
    "Atomic and Molecular Physics, and Optics": "Atomic, Mol & Optics",
    "Nuclear and High Energy Physics": "Nuclear & HE Phys",
    "Condensed Matter Physics": "Condensed Matter",
    "Statistical and Nonlinear Physics": "Stat & Nonlin Phys",
    "Renewable Energy, Sustainability and the Environment": "Renewable Energy",
    "History and Philosophy of Science": "Hist & Phil of Sci",
}

# Per-word replacements (applied when no phrase override matches).
WORD = {
    "and": "&", "And": "&",
    "Management": "Mgmt", "Sciences": "Sci", "Science": "Sci", "Scientific": "Sci",
    "Engineering": "Eng", "Information": "Info", "Systems": "Sys", "System": "Sys",
    "Technology": "Tech", "Psychology": "Psych", "Medicine": "Med", "Medical": "Med",
    "Mathematics": "Math", "Mathematical": "Math", "Statistics": "Stat", "Statistical": "Stat",
    "Probability": "Prob", "Environmental": "Environ", "Mechanical": "Mech", "Electrical": "Elec",
    "Biochemistry": "Biochem", "Molecular": "Mol", "Computational": "Comp", "Computer": "Computer",
    "Development": "Dev", "Developmental": "Dev", "Operations": "Ops", "Behavioral": "Behav",
    "Behaviour": "Behav", "Behavior": "Behav", "Communication": "Comm", "Communications": "Comms",
    "Pharmaceutical": "Pharm", "Pharmacology": "Pharmacol", "Agricultural": "Agric",
    "Manufacturing": "Mfg", "Organizational": "Org", "Conservation": "Conserv",
    "Rehabilitation": "Rehab", "Epidemiology": "Epidem", "Physiology": "Physiol",
    "Microbiology": "Microbiol", "International": "Intl", "Political": "Pol", "Education": "Educ",
    "Educational": "Educ", "Geography": "Geog", "Astronomy": "Astron", "Atmospheric": "Atmos",
    "Materials": "Mtls", "Chemistry": "Chem", "Chemical": "Chem", "Physics": "Phys",
    "Physical": "Phys", "Theoretical": "Theor", "General": "Gen", "Industrial": "Indust",
    "Services": "Svcs", "Service": "Svc", "Reliability": "Reliab", "Nonlinear": "Nonlin",
    "Occupational": "Occup", "Anesthesiology": "Anesth", "Ophthalmology": "Ophthal",
    "Obstetrics": "Obstet", "Gynecology": "Gyn", "Pediatrics": "Pediatr", "Dermatology": "Derm",
    "Cardiology": "Cardiol", "Radiology": "Radiol", "Immunology": "Immunol", "Spectroscopy": "Spectros",
}


def short(name):
    if name in PHRASE:
        return PHRASE[name]
    out = [WORD.get(w, w) for w in name.split()]
    return " ".join(out)


def fetch_subfields():
    rows, cursor = [], "*"
    while cursor:
        r = requests.get("https://api.openalex.org/subfields",
                         params={"per-page": 200, "cursor": cursor, "mailto": MAILTO,
                                 "select": "id,display_name"}, timeout=30)
        d = r.json()
        for s in d.get("results", []):
            rows.append((s["id"].split("/")[-1], s["display_name"]))
        cursor = d.get("meta", {}).get("next_cursor")
    return rows


def main():
    rows = sorted(fetch_subfields(), key=lambda r: r[1].lower())
    lines = [
        "# OpenAlex subfield short labels",
        "",
        "Short labels for the Explore **FIELD** column (the synthetic-field blend). One row per "
        "OpenAlex subfield. Aim for ~≤18 characters so the dominant subfield fits on one line as "
        "`Label 47% · +N more`. **Edit the `short` column freely** — fix anything that reads oddly; "
        "a blank `short` falls back to the full name. `sid` is the OpenAlex subfield id.",
        "",
        f"{len(rows)} subfields. Sorted by name.",
        "",
        "| sid | OpenAlex subfield | short |",
        "|-----|-------------------|-------|",
    ]
    for sid, name in rows:
        lines.append(f"| {sid} | {name} | {short(name)} |")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {OUT} ({len(rows)} subfields)")


if __name__ == "__main__":
    main()

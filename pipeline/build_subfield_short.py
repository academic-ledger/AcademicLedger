"""Parse docs/subfield_abbreviations.md (the hand-edited short-label table) into a TS map the web
imports for the Explore "Fields" column. Re-run after editing the .md, then commit + deploy.

Run: python pipeline/build_subfield_short.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, "docs", "subfield_abbreviations.md")
OUT = os.path.join(ROOT, "web", "lib", "subfieldShort.ts")


def main():
    pairs = []
    for raw in open(MD):
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 3:
            continue
        sid, name, short = cells
        if not sid.isdigit():  # skips the header row and the |---| separator
            continue
        if short and short != name:  # blank or identical -> web falls back to the full name
            pairs.append((sid, short))
    pairs.sort()
    out = (
        "// AUTO-GENERATED from docs/subfield_abbreviations.md by pipeline/build_subfield_short.py.\n"
        "// Do not edit by hand — edit the .md and re-run the script.\n"
        "export const SUBFIELD_SHORT: Record<string, string> = {\n"
        + ",\n".join(f'  "{sid}": "{short}"' for sid, short in pairs)
        + "\n};\n"
    )
    with open(OUT, "w") as f:
        f.write(out)
    print(f"wrote {OUT} ({len(pairs)} short labels)")


if __name__ == "__main__":
    main()

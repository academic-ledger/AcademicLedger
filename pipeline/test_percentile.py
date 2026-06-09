"""Regression tests for the full-population percentile rule (QaL_spec.md §5).

The observed-percentile denominator is the FULL cohort (cited + uncited), never a cited-only
or top-N/sorted sample. These tests pin the behavior that a prior build got wrong, where a
highly-cited paper was ranked against its cited-only co-citation neighborhood and came out at
the ~22nd percentile instead of the ~99th.

Run:  OPENALEX_MAILTO=you@example.com python pipeline/test_percentile.py   (hits OpenAlex; no DB)
"""
import sys

import synthetic_field as sf  # run from pipeline/ on sys.path (python pipeline/test_percentile.py)


def test_valuing_rd_is_top_field_percentile():
    """W2103157313 — 'Valuing R&D Projects', subfield 1408/2007, 221 citations.
    Full-population field-and-vintage percentile must be ~99 (top ~1%), NOT ~22.
    OpenAlex: 1408/2007 has n=57,819, ~69% uncited, ~494 works with >221 cites."""
    pct, p0 = sf.pct_in_cohort("1408", 2007, 221)
    pct100 = round(100 * pct, 2)
    assert 98.5 <= pct100 <= 99.6, f"expected ~99 (top 1%), got {pct100}"
    assert pct100 > 50, f"regression: ranked below median ({pct100}) — cited-only/biased cohort?"
    assert 0.60 <= p0 <= 0.75, f"expected ~0.69 uncited share, got {p0}"
    print(f"  ok: 1408/2007, 221 cites -> {pct100}th percentile (p0={round(p0,3)})")


def test_uncited_atom_takes_mid_rank():
    """An uncited focal sits at the mid-rank of the atom, 100·p0/2 — the uncited mass stays
    in the denominator and is not dropped."""
    pct, p0 = sf.pct_in_cohort("1408", 2007, 0)
    assert abs(pct - p0 / 2.0) < 1e-9, f"uncited should be p0/2={p0/2}, got {pct}"
    print(f"  ok: uncited atom at mid-rank {round(100*pct,2)} = 100*p0/2")


def test_denominator_is_full_population():
    """The percentile of a 1-citation paper must be near the top of the uncited atom
    (~p0), confirming the uncited mass is counted in the denominator, not excluded."""
    pct, p0 = sf.pct_in_cohort("1408", 2007, 1)
    assert pct >= p0 * 0.95, f"1-cite paper ({pct}) should sit at/above the atom mass {p0}"
    print(f"  ok: 1-cite paper at {round(100*pct,2)} (atop the {round(100*p0,1)}% uncited atom)")


if __name__ == "__main__":
    tests = [test_valuing_rd_is_top_field_percentile, test_uncited_atom_takes_mid_rank,
             test_denominator_is_full_population]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"  FAIL {t.__name__}: {e}")
            failed += 1
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)

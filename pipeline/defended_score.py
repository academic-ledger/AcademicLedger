"""Gaming-resistant QaL scoring: self-citation discounting + citation authority-weighting.

Motivation (Exhibit E, analysis/gaming_robustness): QaL's Layer-A observed standing is the mid-rank
percentile of a paper's raw citation count within its (subfield, vintage) cohort. On real data that
count-only ranking is *gameable in the muddy middle of sparse fields* — a feasible ~20-paper citation
ring can lift a median paper into the top decile, because the citation distribution there is so
compressed. Two defenses restore resistance:

  1. SELF-CITATION DISCOUNTING (exact). A citation is discarded if the citing work shares any author
     (disambiguated OpenAlex author id / ORCID) with the target. A self-citation-only attack then nets
     exactly zero — by construction.
  2. AUTHORITY-WEIGHTING. Each surviving citation counts not 1 but h(standing of the citing work), with
     h(s) = s**GAMMA over the citer's own within-field standing s in [0,1]. Fabricated ring members are
     new / uncited works whose standing sits at the field's uncited atom, so their citations carry the
     floor weight h(atom) << mean citation authority — the ring is discounted to a fraction of its size,
     while legitimate papers (whose citers are drawn from the normal standing mix) keep ~their rank.

The DEFENDED count replaces raw `cited_by_count` as the Layer-A ranking key; percentiles, calibration
and conformal intervals are computed exactly as today on the defended count.

STATUS — not yet wired into the served pipeline. Activating it requires an INCOMING-citation-edge
source (per target work: its citing works, each citer's disambiguated authors and its own standing),
which the current ingest does not store (`works.raw` carries no `referenced_works`). That ingestion is
the remaining engineering step; the functions below are the estimator, unit-tested and ready to wire.
Exhibit E validates the design on real field distributions.
"""

GAMMA = 2.0  # authority-weight convexity; see analysis/gaming_robustness (γ=2 default, sensitivity reported)


def authority_weight(standing, gamma=GAMMA):
    """Weight of a single citation whose citing work has within-field standing s in [0,1]."""
    s = 0.0 if standing is None else max(0.0, min(1.0, float(standing)))
    return s ** gamma


def defended_count(citations, gamma=GAMMA):
    """Gaming-resistant citation count.

    citations: iterable of (citer_standing, shares_author) — citer_standing in [0,1] is the citing
    work's own within-field observed percentile / 100; shares_author is True iff the citing work shares
    an author with the target (a self-citation). Returns the authority-weighted, self-citation-discounted
    count that replaces raw cited_by_count as the Layer-A ranking key.
    """
    return sum(authority_weight(s, gamma) for s, shares in citations if not shares)


def ring_equivalent(atom_standing, mean_authority, gamma=GAMMA):
    """Citation-equivalents of ONE fabricated (uncited) ring citation: h(atom)/mean citation authority.
    <1 means the ring is discounted; used by Exhibit E to quantify per-field resistance."""
    return authority_weight(atom_standing, gamma) / mean_authority if mean_authority else 0.0


if __name__ == "__main__":
    # self-citation-only attack nets exactly zero
    assert defended_count([(0.0, True)] * 20) == 0.0
    # a legit citation from a top-standing work counts ~1; from an uncited work ~ atom**gamma
    assert abs(authority_weight(1.0) - 1.0) < 1e-9
    assert abs(authority_weight(0.28) - 0.0784) < 1e-6   # DS uncited atom ~0.28 -> ~0.08 at gamma=2
    # an external ring of 20 uncited works counts far less than 20
    assert defended_count([(0.28, False)] * 20) < 20 * 0.1
    print("defended_score self-test OK")

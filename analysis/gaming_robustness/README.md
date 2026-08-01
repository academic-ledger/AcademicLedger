# Gaming robustness (QaL paper Exhibit E)

Can a strategic author move QaL by manufacturing citations? We attack QaL's **Layer-A observed
standing** — the exact mid-rank percentile transform of raw citation count within a (subfield × vintage)
cohort (`pipeline/calib_lib.pct_of_all`) — on **real eventual-citation distributions** for the four
target fields, and measure how far feasible attacks move a paper, before and after two defenses.

Data: eventual (age-10) citation histograms per cohort from the OpenAlex bulk snapshot
(`pipeline/factory_cohorts.py`, in-region; 2011–2013 vintages, top-2 subfields/field). Attacks are
simulated against each field's representative (largest) cohort.

## The honest finding: resistance is region-dependent

**1. The consequential top tail is structurally protected (saturation).** Advancing a fixed +5
percentile points costs a rapidly growing number of citations as you climb — near the top decile it
takes tens to hundreds of citations per +5 points (`fig_gaming_saturation.png`). Manufacturing a
top-percentile paper is prohibitively expensive.

**2. But count-only QaL is gameable in the "muddy middle" of sparse fields.** Sparse-field citation
distributions are so compressed (a median paper has ~1 citation; the top decile begins in the teens)
that a **feasible ~20-paper citation ring can lift a median paper into the top decile**
(`fig_gaming_injection.png`, solid lines). This is *not* "barely moves" — and it is worst exactly where
the field is sparsest.

**3. The defenses help — but their power tracks density too (`pipeline/defended_score.py`).**
- **Self-citation discounting (exact):** a citation is dropped if the citing work shares an author with
  the target, so a self-citation-only attack nets **exactly zero**, in every field.
- **Authority-weighting:** each surviving citation counts `h(s) = s^γ` on the citer's own standing `s`.
  Fabricated ring members are new/uncited works, so in a **dense** field their citations carry the floor
  weight `h(atom) ≪ mean citation authority` and the ring is heavily discounted — but in a **sparse**
  field, where 70–80% of *all* papers are uncited, an uncited citer is statistically indistinguishable
  from a normal one, so the discount → 1 and weighting has almost nothing to grip. The per-field ring
  discount, computed from each field's **real** standing distribution (γ=2), runs **0.24 (Biochemistry)
  → 0.60 (Arts & Humanities)** — i.e., authority-weighting works where the field is dense and fails
  where it is sparse.
- **The audit trail is the backstop, especially in sparse fields:** where weighting can't help,
  resistance to an external ring rests on structural detection (ring/cartel signatures in the open
  citation graph) plus QaL's wide young-paper intervals — a described defense, not an empirical claim
  made here.

## Results (four fields — real snapshot cohorts, 12k papers each)

A 20-paper citation ring against a paper starting at the 75th percentile; "reached" = percentile after
the attack (top decile begins at p90). Both the raw vulnerability and the defense's power move
monotonically with field sparsity.

| Field | uncited@10y | cites at p90 / p95 / p99 | p75 → count-only | p75 → **defended** | ring discount (γ=2) |
|---|---:|---:|---:|---:|---:|
| Biochemistry & Mol Bio | 46% | 41 / 72 / 215 | p87 | **p79** | 0.24 |
| Decision Sciences | 60% | 14 / 33 / 123 | p93 | **p88** | 0.36 |
| Economics & Finance | 72% | 3 / 9 / 55 | p98 | p96 | 0.59 |
| Arts & Humanities | 81% | 2 / 6 / 31 | p98 | p97 | 0.60 |

**Reading.** In dense Biochemistry a 20-ring can't even reach the top decile (p75→p87) and the defenses
push it to p79; by Decision Sciences the ring reaches the top decile (p93) and the defenses pull it back
out (p88). In the sparse fields the ring lands a p75 paper at p98 and authority-weighting barely moves it
(p96–97) — self-citation discounting still works, but external rings there must be caught structurally.
A self-citation-only attack nets exactly 0 in all four fields. (Uncited fractions from the distribution
exhibit; γ-sensitivity in `gaming_results.json`.)

## Caveats / scope
- Self-citation discounting is exact and needs no modeling. Authority-weighting's *effect on the attack*
  is grounded in each field's real standing distribution; its effect on *legitimate* rankings assumes
  exchangeable citers (legit citers drawn from the field standing mix → weighting is ~rank-preserving).
  Directly measuring legitimate rank preservation needs incoming citation-edge data (who cites whom +
  citer standing), which the current ingest does not store — a scoped follow-up that would also let
  `defended_score.py` run in the served pipeline.
- Attacks are simulated on the representative cohort per field; the qualitative picture (potent in the
  middle of sparse fields, saturated at the top, blunted by the defenses) is stable across cohorts.

## Rerun
```bash
# real four-field histograms from the bulk snapshot (~1h, ~$0.53; needs AWS creds):
../../.venv/bin/python ../../pipeline/run_cohorts_factory.py --file-limit 0 --per 12000
../../.venv/bin/python simulate.py cohorts_hist.json figures      # figures + gaming_results.json
```

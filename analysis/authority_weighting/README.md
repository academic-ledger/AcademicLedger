# Authority-weighting: count vs standing-weight vs PageRank vs TrustRank

Extends Exhibit E (`analysis/gaming_robustness`). Exhibit E showed count-only QaL is gameable in the muddy
middle of sparse fields and that standing-weight (`h(s)=sᵞ`) only helps in dense fields. The natural next
question (partners' request): does **recursive/eigenvector authority — PageRank** close the sparse-field
gap, and how much does it change the *honest* ranking? Two tests:

- **Test 1 — ranking fidelity.** How much does authority-weighting reshuffle the legitimate order vs raw
  count? (Spearman ρ and top-decile Jaccard.) High ⇒ ~free hardening; low ⇒ a genuinely different metric.
- **Test 2 — gaming resistance.** The Exhibit E 20-paper ring attack, run against each metric: the
  percentile a p50/p75/p90 paper *reaches*.

**Data.** A synthetic directed citation graph (Price/preferential-attachment with a recency taper),
calibrated so the citation-count distribution reproduces a **dense** field (~Biochemistry, 42% uncited)
and a **sparse** field (~Arts & Humanities, 75% uncited). This demonstrates the *mechanism* on realistic
densities; the exact magnitudes are model-dependent (see caveats). `pagerank_experiment.py`.

## The finding — the comfortable assumption is wrong

`fig_pagerank_gaming.png`. Percentile a 20-ring lets a paper reach (top decile = p90; ↑ = gamed):

| Metric | Test 1: ρ(count) | dense: p50→ | sparse: p50→ | verdict |
|---|---:|---:|---:|---|
| count-only | 1.00 | p99 | p99.7 | fully gameable (Exhibit E) |
| standing-weight (γ=2) | — | p75 | **p97.5** | helps dense, fails sparse (Exhibit E) |
| **vanilla PageRank** | **0.93–0.97** | p99 | **p95.7** | **≈ as gameable as count** |
| **TrustRank (trust-seeded)** | **0.54–0.58** | p36 | **p44** | **resists — but reshuffles the ranking** |

Two things, both important:

1. **Vanilla PageRank is *not* a gaming fix.** A self-citing ring is a **link farm**, and plain PageRank
   is manipulable by link farms — a classic web-spam result [Gyöngyi et al. 2004]. The "a fabricated ring
   has zero authority" intuition is wrong: every node gets baseline *teleport* mass, and in a citation
   graph where most papers sit near that floor, 20 fabricated inlinks are a large *relative* boost — the
   same compressed-distribution problem count-only has. Vanilla PageRank also tracks count closely (ρ ≈
   0.95), so it is nearly *free* to adopt but buys almost no resistance.

2. **Trust-seeded authority (TrustRank) is the actual fix — at a cost.** If teleport mass goes only to
   *established* seed papers (here, top-decile-by-count), fabricated nodes receive **zero** baseline mass
   and decay to ~0 authority, so the ring cannot lift a paper out of the untrusted floor (p50→p44, i.e.
   *below* where it started). But TrustRank reshuffles the honest ranking heavily (ρ ≈ 0.55 vs count): it
   credits connectivity to the trusted core rather than raw count, which amplifies the Matthew effect and
   can disadvantage genuinely novel-but-legitimate work.

**Bottom line: resistance and fidelity trade off, dialed by how much of the teleport mass is
trust-seeded.** Vanilla PageRank ≈ count (high fidelity, low resistance); full TrustRank ≈ resistant but
low fidelity. The design question is where to set the dial (partial trust-seeding), and to monitor the
Matthew-effect cost — not "assume PageRank is hard to game."

## Caveats
- **Synthetic graph.** The *qualitative* findings are mechanism-driven and robust — vanilla PageRank's
  link-farm gameability is a known result; TrustRank's ring-resistance is by construction; the
  fidelity/resistance trade-off is directional. The *magnitudes* (ρ, reached percentiles) depend on the
  generative model and need confirmation on the real citation graph.
- **Real-graph confirmation (next step).** Compute all four metrics on the real OpenAlex within-field
  citation graph for the four target fields, and rerun both tests. This needs the incoming-citation-edge
  ingestion (the same dependency as wiring `pipeline/defended_score.py`). The heavy graph build + PageRank
  can run in-region on the snapshot factory, emitting only the compact test statistics.

## Rerun
```bash
../../.venv/bin/python pagerank_experiment.py .    # writes pagerank_results.json + fig_pagerank_gaming.png
```

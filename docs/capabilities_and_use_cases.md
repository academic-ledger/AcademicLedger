# Capabilities and Use Cases

*Internal ideation memo for Cachon, Terwiesch, and Ulrich. Draft, not a build specification, not linked from the site. June 2026. Now that the full OpenAlex citation graph is indexed (EC2), most of these move from "the 30 faculty" to "anyone."*

---

## The three superpowers everything here rests on

1. **The calibrated eventual-QaL forecast** — a per-paper posterior over eventual percentile, with an honest interval, decided late.
2. **Synthetic-field placement** — each paper (and author) located in its true intellectual community via the recency-weighted reference-and-citation neighborhood, robust to OpenAlex's single-label misclassification.
3. **The corrections / membership layer** — verified identity and attributed, transparent edits.

Plus the asset the full index now provides: the entire citation graph (references and citers), all authors, venues, topics/subfields, counts-by-year, and abstracts. Each capability below is tagged for what it needs: **[have]** = the current data and metric support it; **[+ingredient]** = needs one added piece (named).

---

## 1. Reference and integrity (the AI-grounding layer — proposed flagship)

- **Reference checker.** Verify every citation in a draft exists and resolves to a real record; flag fabricated or hallucinated references. Acutely timely for LLM-written bibliographies. **[+ reference parsing/resolution]**
- **Retraction and supersession screen.** Flag cited work that is retracted, under an expression of concern, or superseded by a better/newer version. **[+ Retraction Watch via Crossref; version links]**
- **"Did you miss the obvious one?"** Surface high-QaL papers in the draft's synthetic field that it fails to cite but probably should. **[have]**
- **Reference-list diagnostics.** Show the QaL distribution and field-mix of what a paper cites — are you building on strong work, and from where. **[have]**
- **Expose it as an API / MCP tool** that AI writing assistants call, so academic Ledger becomes the trust-and-grounding layer for AI-assisted scholarship. **[+ thin API surface]**

## 2. Discovery and recommendation

- **Feed for your synthetic field.** Recent, high-QaL work in your field-mix. **[have]**
- **"Papers Duncan Watts knows that might interest me."** The intersection of another scholar's citation neighborhood with yours — curated discovery through a mind you trust. **[have]**
- **Rising stars.** Young papers whose QaL posterior is already high with a tightening interval — decide-late discovery of work likely to matter, flagged early. **[have]**
- **Sleeping beauties.** Papers whose observed standing lags what their neighborhood predicts; the under-cited gems. **[have]**
- **Cross-disciplinary bridges.** Papers at the overlap of your field and a target field you want to enter. **[have]**
- **Reading-list / syllabus builder.** The top-QaL canon for a subfield and vintage. **[have]**
- **Semantic "more like this"** beyond the citation graph (for very new papers with few links). **[+ title/abstract embeddings]**

## 3. Self-insight for authors

- **Where your work resonates.** The subfields where your papers land highest — you punch above your weight in X. **[have]**
- **Intellectual fingerprint.** The synthetic-field blend across your whole body of work, and how it has drifted over your career. **[have]**
- **Find your audience.** Which communities cite and co-cite you most — useful for venues, talks, collaborators. **[have]**
- **Forecast tracking.** Watch a paper's QaL interval narrow over time, with a notification when it crosses a confidence threshold. **[have]**

## 4. Finding and matching people

- **Expert finder, done rigorously.** The central authors in a given synthetic field — for co-authors, letter-writers, speakers, panels. **[have]**
- **Reviewer matching.** Align a submission's synthetic field with reviewers whose field overlaps (an editor's tool). **[have]**
- **Venue fit.** Given a draft's field-mix and QaL forecast, suggest where it belongs. **[have]**

## 5. Field-level and meta-science

- **Research-front tracking.** Bibliographic-coupling clusters of recent work reveal live fronts and can alert when a new one forms. **[have]**
- **What's emerging in subfield X.** Topic growth and early-QaL spikes. **[have]**
- **Calibration as a dataset.** The per-subfield half-lives and tail shapes are themselves a meta-science resource — how fast each field resolves — publishable and openly shareable. **[have]**

## 6. Distribution and integrations

- **Browser extension** that badges QaL on any paper you view (Google Scholar, arXiv, journal pages). **[+ extension + API]**
- **Zotero / reference-manager and Overleaf plugins** that audit your library and bibliography for QaL, retractions, and supersession. **[+ plugins + API]**

## 7. Evaluation and institutional (handle with the guardrail below)

- **Honest portfolio view** of a candidate or unit: per-paper, interval-bearing, no single number — the explicit antidote to the h-index and JIF. **[have]**
- **Department / lab / funder dashboards** of output QaL and field coverage, without rolling up to a rank. **[have]**

---

## The guardrail (non-negotiable)

The evaluation uses in §7, and any author-facing feature, must respect the no-single-author-score principle and gaming-resistance by construction. Present per-paper, decide-late, interval-bearing views; never a personal scalar or a ranking of people. Framed that way, "a principled input for committees that refuses the single number" is itself a differentiated pitch rather than a betrayal of the metric.

## What I'd build first

1. **The reference-integrity / AI-grounding suite** (reference checker + retraction-and-supersession screen + missing-key-reference), exposed via a thin API/MCP. It uses the core assets, it is timely, and it gives tool-builders and non-academics a reason to hit the Ledger every day — the kind of traffic that makes the membership and the trust mission real. Smallest added ingredients: reference resolution and the Retraction Watch feed.
2. **Synthetic-field discovery plus rising stars.** The clearest showcase of what only QaL can do (forecast-native discovery), built almost entirely on what exists.
3. **Author self-insight** (where your work resonates, fingerprint, find-your-audience). It extends the author page already built, has strong personal pull, and is the natural on-ramp to membership.

## Throughline

Nearly every item is a recombination of forecast + placement + corrections. The reference-integrity suite turns the Ledger into infrastructure others build on; the discovery and self-insight features turn it into a daily destination; the meta-science outputs make it a public good worth citing. Related docs: `QaL_spec.md`, `QaL_whitepaper.md`, `community_and_business_model.md`.

# Constructing the Ledger from the Public Record

*Memo, June 2026. What can be assembled, within terms of use, to mint a rateable Ledger entity and compute QaL, pointing back to a canonical record rather than hosting it. Sources and licenses verified; re-check at build time, as terms change.*

## The entity model (the crux)

A Ledger entity is not a hosted paper. It is a thin record of a work, keyed by a stable identifier and pointing back to wherever the canonical version lives (journal, arXiv, SSRN, a lab page). The entity carries the QaL estimate, the tier status, and links to its locations; the bytes stay with the host.

The natural primary key is the OpenAlex Work ID, with the DOI and the arXiv ID as alternates, because OpenAlex already deduplicates versions (preprint plus version of record) and records each location. To mint an entity for something not yet in OpenAlex (a brand-new preprint), seed it from a DOI, an arXiv ID, or an ORCID-authenticated author submission, then enrich it as the open feeds catch up. This is exactly the overlay posture: we create and rate the entity; we never need to be the host.

## The open backbone (fully reusable, bulk-ingestible, no TOS problem)

These are the spine of QaL and require no scraping of any walled platform:

- OpenAlex (CC0; REST API plus a full snapshot on AWS). Works, authors, institutions, sources, topics and fields, the citation graph, and OA status. This is the entity key, the citation substrate, and the field-and-vintage normalization base. We already pull from it.
- Crossref (open metadata API; reference lists increasingly open via the Initiative for Open Citations). DOIs, references, funders, licenses. Crossref also now hosts the openly available Retraction Watch database.
- OpenCitations (CC0 open citation index). A clean citation graph for authority-weighting (PageRank or eigenvector style), independent of any vendor.
- ORCID (public data file, CC0; API). The identity layer, and the mechanism for authors to claim and curate their works, which feeds the integrity gate.
- Semantic Scholar Academic Graph (free API and bulk datasets). Supplementary citations, co-citation, influential-citation flags, and embeddings for topic neighborhoods.
- Unpaywall and DOAJ. Open-access status and journal vetting.

Together these already yield a credible, article-level, field-and-vintage-normalized QaL: percentile classes from OpenAlex, RCR-style co-citation normalization from the citation graph, authority-weighting from OpenCitations, identity from ORCID. All open, all within terms.

## Preprints and early-usage signals

- arXiv. Metadata is CC0 and bulk-harvestable via OAI-PMH (the preferred route), with full text and source on Amazon S3 (requester-pays) and a CC0 metadata dump on Kaggle. Reuse is permitted commercially and non-commercially; if you index full text you must link back to arXiv. Covers physics, math, CS, statistics, economics, and quantitative finance. Fully usable.
- bioRxiv and medRxiv. Open API (api.biorxiv.org) that includes per-preprint download and usage statistics, a genuine early-usage signal, which SSRN does not expose. Biology and medicine.
- RePEc, with CitEc (citations) and LogEc (downloads and abstract views). The route for the working-paper download-to-citation signal in economics, the same family as our early-signal study.
- OSF Preprints, Research Square, and similar each offer APIs as well.

## The SSRN constraint (the honest limit)

SSRN cannot be scraped within terms. Elsevier's terms prohibit robots, spiders, and other automated programs to search, screen-scrape, extract, or index the site, and reserve all rights including for text and data mining and AI training. There is no open public API for bulk SSRN metadata; Elsevier's TDM API is for subscribed ScienceDirect content via a personal, non-commercial key, not a route to bulk SSRN data.

So the Ledger does not scrape SSRN. It reaches SSRN-posted work indirectly: many SSRN papers carry DOIs (the "SSRN Electronic Journal" Crossref records) and are indexed in OpenAlex and Crossref, so their metadata and citations arrive through the open backbone, and the Ledger entity simply lists the SSRN page as one location. SSRN-proprietary signals, its download counts, PlumX, and rankings, are off-limits. Net: SSRN coverage is partial and indirect, which is acceptable because the citation-based QaL does not depend on SSRN's internal numbers.

## Correctness signals (open)

- Retraction Watch database, now openly available via Crossref: retractions, corrections, and expressions of concern. The key correctness penalty input to QaL.
- NIH iCite: the Relative Citation Ratio computed for PubMed and biomedical literature, openly.
- Data and code citation via DataCite, Zenodo, and OpenAlex links; replication links where recorded.

## What is not openly available (design around it)

- Altmetric and PlumX attention scores are proprietary.
- Web of Science and Scopus are paid; Dimensions has only a limited free tier.
- SSRN and Elsevier internal usage statistics are closed.

Building QaL on the open stack and treating these gated attention metrics as optional or excluded is not just a constraint, it is better practice: it keeps the metric transparent, auditable, and harder to game, consistent with the Leiden Manifesto.

## Recommended minimal data spine (buildable today, fully within TOS)

- Primary key: OpenAlex Work ID, plus DOI and arXiv ID.
- Citations and field/vintage normalization: OpenAlex plus OpenCitations plus Crossref references, giving percentile classes, MNCS-style normalization, and RCR-style co-citation normalization.
- Identity and integrity: ORCID.
- Preprints and early usage: arXiv (OAI-PMH and S3), bioRxiv (API downloads), RePEc/LogEc (economics downloads).
- Correctness: Retraction Watch via Crossref, iCite where applicable.
- Entity: a thin Ledger record pointing to the canonical location(s), with QaL computed and refreshed from these feeds; SSRN reached only through the open aggregators.

This is enough to compute a credible QaL for a covered field now, with no dependence on scraping SSRN and no dependence on proprietary attention metrics. It is also exactly the cold-start-proof Bundle 0 (the Lens): the metric over the public corpus, before any participant joins.

## Flags

- Coverage and citation completeness vary by field and source; OpenAlex is strong but not perfect, and law and the humanities are undercounted by citation-based methods.
- arXiv full-text reuse requires a link-back; respect per-record licenses in the OAI-PMH metadata.
- Verify each source's license and terms at build time; they change. SSRN's no-scraping terms are current as of mid-2026 and should be re-checked.

## Sources

- SSRN Terms of Use (Elsevier), https://www.ssrn.com/index.cfm/en/terms-of-use/ ; Elsevier text-and-data-mining policy, https://www.elsevier.com/about/policies-and-standards/text-and-data-mining
- arXiv bulk data and reuse: https://info.arxiv.org/help/bulk_data.html ; OAI: https://info.arxiv.org/help/oa/index.html ; S3: https://info.arxiv.org/help/bulk_data_s3.html
- OpenAlex (CC0, API and snapshot): https://openalex.org ; Crossref: https://www.crossref.org ; OpenCitations: https://opencitations.net ; ORCID: https://orcid.org ; Semantic Scholar API: https://www.semanticscholar.org/product/api
- bioRxiv API: https://api.biorxiv.org ; RePEc/CitEc/LogEc: https://citec.repec.org , https://logec.repec.org
- Retraction Watch via Crossref: https://www.crossref.org/blog/news-crossref-and-retraction-watch/ ; NIH iCite: https://icite.od.nih.gov

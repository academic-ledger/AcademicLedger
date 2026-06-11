# Community and Sustainable Business Model

*Internal strategy memo for Cachon, Terwiesch, and Ulrich. Draft, not ready for prime time. This is a strategy document, not a build specification, and it is deliberately not linked from the site. June 2026.*

---

## 1. The problem it solves, twice

Two problems share one mechanism.

**Data quality, at the source.** OpenAlex is the open spine of the Ledger, and it has real errors: an author credited with a German book on museology they did not write, Joseph Simmons placed at the "California University of Pennsylvania," indexed items that are obsolete or superseded by better versions. The cheapest, highest-quality source of corrections is the people who know best, the authors themselves. Letting them curate their own records is both the best fix and a magnet for engagement.

**Sustainability, without betraying the principles.** The Ledger is a non-commercial public good built on open data, with an open method and open code. It cannot fund itself by paywalling the metric, selling the data, or running ads without becoming the thing it set out to replace. A membership model, dues paid by individuals (and reimbursable from university funds), funds the work the way a scholarly society or a public-radio membership does, and keeps the metric, the data, and viewing free for everyone.

## 2. The model

Membership is the right to curate your own scholarly record on the Ledger and to be recognized as a verified, contributing member. Concretely, a member can claim or disavow a paper, attach an ORCID, correct an affiliation, link a record to a superseding version, and annotate their own records. Edits are stored transparently as an attributed overlay, never silently overwriting the open record, with a per-page "show corrections" toggle so the original and the curated view are both visible. Members carry a verified badge.

A virtuous loop: verified corrections are pushed back upstream to OpenAlex. The Ledger does not become a competing source of truth; it repairs the commons it depends on, which is a better story and avoids forking the record.

## 3. The line between free and member

The metric, the data, and viewing stay free for everyone, and anyone can flag a suspected error, Wikipedia-style. Membership buys verified-claim authority, the badge, the richer curation features, and the standing of supporting the commons. This framing matters: dues must read as belonging to a non-commercial commons, not as a ransom to fix errors the Ledger made about you, because self-curation is already free on Google Scholar profiles, ORCID, Scopus author feedback, and Web of Science researcher profiles (formerly Publons). The willingness to pay comes from mission support plus low-friction reimbursement plus the badge, not from gatekeeping basic corrections.

Equity is a principle, not an afterthought: a fee-waiver path for students, independent scholars, and underfunded regions keeps the Ledger from becoming a rich-institution club, which would undercut the open public-good brand.

Indeed, there could be a "no questions asked" free tier with some friction. Write an email, wait for a response, etc. Hopefully most people would opt to pay the 20 bucks to be a member...

## 4. The safeguard that makes self-curation safe

Because the Ledger deliberately computes no author-level score, self-curation cannot game any QaL number. Claiming or disavowing a paper changes attribution and what appears on an author page; it does not change that paper's quality estimate, and there is no author aggregate to inflate. This removes the standard objection to letting a rated party edit the inputs, an objection the incumbents who sell author and institution scores cannot escape.

## 5. Scope and verification (what a member may edit, and how it is checked)

Keep two things apart. Curating your **own** record is the initial membership. Annotating **other people's** records, and post-publication commentary, is the socially fraught community layer; it stays later and governed.

| Edit | Who | Verification | Affects QaL? |
|---|---|---|---|
| Claim a paper | member | ORCID match or co-author confirmation | No (attribution/display only) |
| Disavow a paper | member | ORCID/co-author check; cannot unilaterally rewrite a co-authored work | No |
| Add/correct ORCID | member | ORCID OAuth | No |
| Correct affiliation | member | institutional email or ORCID employment | No |
| Link superseded-by / version | member or flagger | shown as an attributed link, reversible | No |
| Note on own record | member | attributed, transparent | No |
| Flag a suspected error | anyone (free) | queued, not auto-applied | No |

Nothing a member can do moves a paper's QaL; everything is attributed and visible under the toggle; authorship changes require identity verification, not bare assertion. Abuse and defamation handling (especially once commentary on others is allowed) is a governance task for the later layer.

## 6. The numbers, and why 50,000 is the ambition, not the threshold

Infrastructure is cheap: OpenAlex usage is on the order of a dollar a day, hosting is modest, and the snapshot is free. The real cost is people. So the viability threshold is far below the headline number.

| Members | Dues $29 | Funds |
|---|---|---|
| 2,500 | | $72.5k |
| 5,000 | | $145k |
| 10,000 | | $290k |
| 25,000 | | $725k |
| 50,000 | | $1.45M |

Roughly: five to ten thousand members sustains a lean operation (one or two people plus infrastructure); fifty thousand funds a real organization (a small team). Scholarly societies sustain themselves at tens of thousands of members at comparable dues, and the addressable universe is large, millions of active researchers, with ORCID alone holding well over ten million registered iDs. Fifty thousand is plausible but it is the ambition; the project does not need it to be alive.

A complementary lever worth modeling: **institutional or library site licenses.** University libraries already pay for Web of Science and Scopus; a low-cost open alternative is attractive, and a few hundred institutions at a few thousand dollars each would reach the same total as fifty thousand individuals, with a far smaller sales motion. Individual dues build the community and the data; institutional licenses may carry the budget.

## 7. Sequencing (the chicken and the egg)

People pay to be correctly represented on a surface that matters, and the surface matters once it has trusted coverage. So build credibility and coverage first, free, and turn on dues only once being mis-rendered on the Ledger is worth $29 to fix. Gating too early starves both adoption and goodwill. The order is: earn trust, then invite membership.

## 8. Where this sits in the roadmap

This is not a bolt-on. It is the first fundable bundle of the participant layer that has been deferred in the spec as the "community layer," the layer that eventually carries the Refereed and Canon tiers and the ORCID-verified identity. Membership-plus-curation is the on-ramp to all of it, and it earns its keep immediately by improving the data that the synthetic field and author disambiguation depend on.

## 9. Open questions to decide

- Legal entity for dues (a non-profit/association structure that makes "reimbursable from university funds" clean).
- The exact free-versus-member line, and the fee-waiver policy.
- Individual dues versus institutional site licenses as the primary engine.
- Governance for the later community layer (annotating others, disputes, defamation).
- Whether and how to formalize the upstream corrections feed to OpenAlex.
- Timing: how much coverage and trust before dues are introduced.

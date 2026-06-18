# Community Layer v0: Identity and Curation

*Build spec for the first slice of the participant/community layer. Repo-internal, not linked from the site. June 2026. Companion to `community_and_business_model.md` (the why) and `QaL_spec.md` (the metric, which these features must not change). We start in Claude Code with Story 1 (ORCID sign-in).*

---

## What's new architecturally (read this first)

Until now the app is effectively read-only: it constructs a paper page from OpenAlex plus cached QaL and serves precomputed tables, and `web/API_CONTRACT.md` is a read API. This slice introduces the first **authenticated writes**, which is the fundamental change Karl flagged:

- Authentication and sessions (ORCID OAuth).
- A write API (add authenticated mutation endpoints alongside the read API).
- New user-data tables for the overlay (`users`, `claims`, `paper_notes`), kept separate from the compute/metric tables.
- A **display-merge** step that overlays user contributions onto the OpenAlex-derived record at render time.

**Hard boundary:** the overlay is additive and never mutates the metric or data tables (`works`, `cohort_percentiles`, `calibration_models`, `qal_records`, `synthetic_field`). Curation changes attribution and display only; it never changes a paper's QaL. Everything is attributed, dated, reversible, and shown under a "show corrections" toggle, with the original OpenAlex view always one click away.

## Principles carried from the business model

- Transparent, attributed overlay; never a silent overwrite; show-corrections toggle.
- No QaL change and no author-level score (so curation has no metric to game).
- v0 scope is curating your **own** record; commenting on others is the later governed layer.
- Honest confidence labels: ORCID-confirmed vs self-claimed.
- Free, not gated behind dues (dues are a later slice).
- ORCID OAuth only; no passwords stored.

## Shared data model (new, user-data side; never write the metric tables)

- `users`: id, orcid_id (unique), display_name, created_at, last_login_at. No password.
- `orcid_works`: user_id, the member's works (DOIs / OpenAlex Work IDs) pulled from their ORCID record at login; used to confirm authorship.
- `claims`: id, user_id, work_oaid, author_position (which byline slot), status (`self_claimed` | `confirmed` | `disputed` | `withdrawn`), source (`orcid_works` | `self_assert` | `coauthor` | `orcid_push`), created_at.
- `paper_notes`: id, user_id, work_oaid, body (text), optional structured fields (`supersedes_oaid`, `cite_instead_oaid`), visible (bool), status, created_at, updated_at.
- Display-merge: at render, join the OpenAlex-derived record + `qal_records` with any `claims`/`notes` for that work, rendered as the attributed overlay under the toggle.

Secrets: `ORCID_CLIENT_ID` / `ORCID_CLIENT_SECRET` in `.env` and GitHub Actions secrets; store the minimum from OAuth (iD, name, and the works list); never store a password.

---

## Story 1 — Sign in with ORCID

*As a researcher, I can sign in with my ORCID so the Ledger knows who I am, verified.*

Acceptance:
- ORCID OAuth (sandbox first, then production), e.g. Auth.js / NextAuth with the ORCID OIDC provider.
- On first login, create a `users` row keyed by ORCID iD with display name and iD; subsequent logins load it.
- Session login/logout; a small "signed in as [name], ORCID verified" indicator; no passwords stored.
- On login, fetch and cache the member's ORCID works (DOIs / Work IDs) into `orcid_works`, for Stories 2 and 3.
- Out of scope: dues, profile editing, any write to a paper.

## Story 2 — Author note on your own paper

*As a signed-in author, I can add a short public note to a paper I authored, e.g. "early working paper; please cite W2234445."*

Acceptance:
- The note box appears only on papers whose DOI/Work ID is in the member's `orcid_works` (authorship confirmed), or on a paper the member has claimed (Story 3).
- Free text plus an optional structured "superseded by / cite instead: [Work ID]" field (feeds the future reference-checker and an upstream-to-OpenAlex path).
- Renders on the paper page attributed to the member with ORCID and a "verified author" label and date, under the corrections area with the show-corrections toggle.
- Member can edit or delete their own note; does not change QaL; rate-limited; takedown path.
- Out of scope: notes on papers you did not author or claim, replies/threading, dues.

## Story 3 — Claim a paper

*As a signed-in author, I can claim authorship of a paper whose byline includes a name that matches me but that OpenAlex has not linked to my ORCID, so it is correctly attributed to me on the Ledger and added to my profile.*

Acceptance:
- On a paper page, for a byline author slot not linked to an ORCID (or linked to a clearly different author entity), a signed-in user whose name plausibly matches that slot sees a "This is me, claim" control tied to that specific position.
- Claiming writes a `claims` row attaching the user's ORCID to that slot, shown as "Claimed by [name], ORCID verified, [date]" under the corrections area with the toggle. It does not overwrite the OpenAlex record and does not change QaL.
- The paper is added to the member's Ledger profile and unlocks the Story-2 note for that paper.
- **Verification and honesty:** because a claimed paper is by definition not in the member's ORCID works (else no claim is needed), the claim rests on name-match plus the member's verified identity asserting it. Label it `self_claimed`, distinct from an ORCID-confirmed link. Offer a deep link to add the work to the member's ORCID record (the durable, upstream-propagating fix); when ORCID later confirms it, upgrade to `confirmed`.
- **Safeguards:** the name must plausibly match the byline slot; a claim cannot remove or overwrite another correctly-credited author; claims are reversible by the claimant and publicly contestable (a co-author or anyone can dispute, flagging for review); rate-limited. Because there is no author score, a false claim gains no metric, only a visible, accountable, contestable attribution.
- Out of scope: disavowing or removing someone else's attribution, merging/splitting OpenAlex author entities, bulk one-click profile claim, dues.

---

## Cross-cutting

- **Verification spectrum and labels.** `confirmed` (ORCID works match or ORCID-propagated) vs `self_claimed` (name-match + asserted). Always show which; never let a self-claim read as a verified link.
- **Reversibility and contestability.** Every overlay item is editable/removable by its author and disputable by others; disputes flag for review (resolution machinery is the later governed layer).
- **ORCID-push upstream.** Where possible, nudge the durable fix: add the work to ORCID, which flows to OpenAlex over time, so the Ledger repairs the commons rather than forking it.
- **Privacy and secrets.** ORCID OAuth; store the minimum; secrets in env and Actions, never committed.
- **Out of scope for v0.** Disavow (Story 4, later; same overlay/contest machinery, more sensitive because of co-authored works), commentary on others' papers, dues, author-entity merge/split, bulk claim.

## Build order

Story 1 (the identity rail) first, then Story 2, then Story 3. Story 3 re-enables Story 2's note on claimed papers. Disavow follows as Story 4 once the dispute/governance path is fleshed out.

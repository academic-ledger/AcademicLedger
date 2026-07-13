# Start here — onboarding for a new collaborator

Welcome. This project is **academic Ledger / QaL** — a calibrated, field-normalized estimate of a
paper's *eventual* standing in its field, reported as a percentile with an honest interval, built
from the open scholarly record. Live at **academic-ledger.org**. Read `CLAUDE.md` and
`docs/QaL_spec.md` for the full picture; this file just gets you set up and productive.

You do **not** need to be a programmer to contribute. The best early contributions use your domain
judgment, not code.

## 0. Accounts to have

- **Claude Pro or Max** — Claude Code (the AI coding agent we use) needs a paid plan; a free Claude
  account won't include it.
- **A GitHub account** — then ask Karl to add you to the **`academic-ledger`** org with write
  access. (The repo is public, so you can read it without that, but you need write access to open
  pull requests the simple way.)
- **A Markdown (.md) editor** — optional; Claude Code can edit files for you.

## 1. The mental model (read this first)

Claude Code is an **AI agent that works on a copy of this repository** — either in the cloud or a
folder on your computer — and it uses `git` to sync that copy with GitHub. You talk to it in plain
English ("explore this data," "draft this section," "fix this bug"); **it does the git, the
branches, the commits, and the pull requests for you.** You do not need to learn git or the
terminal to start.

## 2. Fastest start (zero install) — Claude Code on the web

1. Go to **claude.ai/code** and sign in with your Claude account.
2. Connect GitHub, authorize the **`academic-ledger`** organization, and pick the
   **`AcademicLedger`** repository.
3. Give it this first prompt to orient yourself:
   > "Read CLAUDE.md and docs/QaL_spec.md, then give me a tour of this project — what QaL is, how
   > it's computed, and where the data lives."

That's enough to explore the code, read the docs, run data analysis, and draft documents — no local
setup needed.

## 3. Later: running the live app or pipeline locally

Only needed when you want to run the website or the data pipeline on your own machine (not required
for the early wins below).

1. Install the **Claude Code desktop app** (Windows/Mac) and sign in.
2. Open the cloned repo and tell it: *"help me set up this project."* It will install the
   dependencies and walk you through creating a `.env` file.
3. You'll need your **own** Neon (database) and Vercel (hosting) access for the full stack — ask
   Karl to invite you. Never copy someone else's credentials, and never commit a `.env`.
4. Activate the shared git hook once: `git config core.hooksPath githooks`.

## 4. How we work together (rules your Claude already follows)

These are in `CLAUDE.md`, which your Claude reads automatically — but good to know:

- **Never push to `main`.** Work on a branch and open a pull request. `main` auto-deploys to
  production (academic-ledger.org), so it's protected — direct pushes are blocked.
- **`pipeline/` and `db/` changes need a second reviewer** (they write production data). Changes to
  the website and docs self-merge once the PR is open.
- **Secrets never get committed.** `.env` is ignored by git; keep it that way.
- When in doubt, ask your Claude to explain what a change will do before you merge it.

## 5. Early wins — pick one

All of these are safe (they land in `docs/` or are read-only), so they can't affect production.

1. **Face-validity audit of QaL** *(great first task, no code).* Pick 15–20 papers you know cold —
   your own, canonical papers in your field, a few you think are over- or under-rated — look them
   up on academic-ledger.org, and note where QaL matches your judgment and where it surprises you.
   Write it up as a short memo in `docs/`. This feeds the whitepaper's validation section and
   reliably surfaces real bugs.
2. **Reference-checker stress test.** Paste bibliographies from your own papers (plus a few made-up
   references) into the "Check references" tool on the site; log any misses or false flags.
3. **Data analysis in your field.** Ask your Claude to pull OpenAlex data for a subfield you know
   and reproduce or extend the citation-distribution analysis (the heavy-tail / uncited-mass
   exhibit), or characterize a field QaL doesn't yet cover. Read-only, uses only the open OpenAlex
   API. Produces a figure + writeup that can become a whitepaper exhibit.
4. **Whitepaper co-authoring.** Draft or critique a section of `docs/all_you_need_is_qal_outline.md`
   with Claude in your Markdown editor.

**Save for later:** website code and anything in `pipeline/` or `db/` — those are riskier and/or
gated, best tackled once you're comfortable.

## 6. Stuck?

Ask your Claude first ("why did that fail?", "how do I open a PR for this?"). Then ping Karl.

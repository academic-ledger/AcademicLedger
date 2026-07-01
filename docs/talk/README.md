# Talk — canonical source

The seminar talk *"All You Need is QaL: The Crisis in Academic Publishing"* lives here.

## Files

- **`master_presentation.md`** — the **canonical source**. A [Marp](https://marp.app/) deck.
  Render to PDF with the "Marp for VS Code" extension, or on the CLI:
  ```
  marp docs/talk/master_presentation.md -o deck.pdf
  ```
- Figures are **not** duplicated here — they are shared with the web app at
  [`web/public/images/`](../../web/public/images/) and referenced as `../../web/public/images/…`.

## The hosted deck is generated — edit only the `.md`

The site serves a reveal.js deck at `/talk`, from [`web/public/talk.html`](../../web/public/talk.html).
**That file is generated from `master_presentation.md` — never edit it by hand.**

```
python pipeline/render_talk.py      # regenerate web/public/talk.html from this .md
```

A **git pre-commit hook** runs this automatically: whenever `master_presentation.md` is part of a
commit, `talk.html` is regenerated and staged, so the two can never drift. The hook lives in
`.git/hooks/pre-commit` (not version-controlled); if you re-clone, reinstall it — the body is a
three-line shell script that greps the staged file list and calls `render_talk.py`.

The render is intentionally a **clean, simple** reveal deck — it reproduces the content and
structure of the Marp source, not the bespoke per-slide inline styling the original hand-built deck
carried (e.g. tier markers show as `[Certified]` code chips rather than colored pills). HTML comments
in the `.md` become reveal **speaker notes** (press **S** in the deck). To present full-screen, open
`/talk.html` directly and press **F**.

## History

- Moved into the repo from Google Drive on 2026-07-01 to establish a single canonical location.
- A second Drive file, `master_presentation-KU2.md`, was a **superseded fork**: older, and missing
  the *"Designing QaL: Composition and Choices"* slide that this version carries. It was not brought
  over.
- On 2026-07-01 the hand-built `talk.html` was replaced by the generated one, making the `.md` the
  single source. The prior deck's hand-tuned per-slide styling was not carried over (accepted
  trade-off for single-sourcing).

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

## Relationship to the hosted deck

The site serves a **separate** reveal.js deck at `/talk`, from
[`web/public/talk.html`](../../web/public/talk.html). It is a hand-maintained twin of this
Marp source — **same slide order and content, but not generated from it.** When you change one,
mirror the change into the other so they don't drift.

## History

- Moved into the repo from Google Drive on 2026-07-01 to establish a single canonical location.
- A second Drive file, `master_presentation-KU2.md`, was a **superseded fork**: older, and missing
  the *"Designing QaL: Composition and Choices"* slide that this version carries. It was not brought
  over.

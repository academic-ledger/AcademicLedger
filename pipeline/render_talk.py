"""Render docs/talk/master_presentation.md -> web/public/talk.html (the reveal.js deck at /talk).

The Marp markdown in docs/talk/ is the single canonical source for the talk. This script
generates the hosted reveal.js deck from it: each Marp slide (--- separated) becomes a
reveal <section>, Marp image sizing (![h:340]) and the `_class: lead` directive are honored,
and HTML comments become reveal speaker notes (press S in the deck).

The render is intentionally *clean/simple* — it reproduces the content and structure of the
Marp source, not the bespoke per-slide inline styling the old hand-built deck carried.

Re-run whenever the talk changes:  python pipeline/render_talk.py
(A git pre-commit hook runs this automatically and stages web/public/talk.html.)
"""
import os
import re
import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "docs", "talk", "master_presentation.md")
OUT = os.path.join(ROOT, "web", "public", "talk.html")

# Marp references figures relative to the source; the hosted deck serves them from /images.
IMG_FROM = "../../web/public/images/"
IMG_TO = "images/"

# Marp `_class:` values -> reveal <section> classes (only `lead` is used today).
CLASS_MAP = {"lead": "center"}

# Head + reveal chrome, reused from the hand-built deck so the site framing, fonts, and the
# custom helper classes (.small .ref .chip .cvline .credit ...) stay identical. Slides are
# injected at <!--SLIDES-->. Generic table styling is added here since the Marp source uses
# markdown tables rather than the old deck's bespoke per-slide <style> blocks.
TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Talk · academic Ledger</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='22' fill='%23111'/%3E%3Ctext x='51' y='70' text-anchor='middle' fill='white' font-family='Georgia,serif' font-size='58'%3E%3Ctspan font-style='italic'%3Ea%3C/tspan%3E%3Ctspan%3EL%3C/tspan%3E%3C/text%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.1.0/reveal.min.css">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.1.0/theme/white.min.css">
<style>
  .reveal, .reveal h1, .reveal h2, .reveal h3, .reveal h4,
  .reveal p, .reveal li, .reveal blockquote {
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }
  .reveal h1 { font-size: 28pt; color: #1b2a4a; text-transform: none; }
  .reveal h2 { font-size: 18pt; color: #1b2a4a; text-transform: none; }
  .reveal section { text-align: left; }
  .reveal section.center { text-align: center; }
  .reveal ul { width: 100%; }
  .reveal ul, .reveal ol, .reveal li, .reveal p { font-size: 16pt; }
  .reveal ul ul li { font-size: 14pt; color: #444; }
  .reveal img { display: block; margin: 14px auto 0; max-height: 60vh; box-shadow: none; border: 0; }
  /* Two-column rows (text beside a figure). The Marp source lays these out as a bare flex row
     without column sizing, and markdown wraps the image in a <p>; without help the figure keeps
     its natural width and overlaps the text. Fix: make the text column flex to fill remaining
     space, let the figure column shrink, and cap the image to its column (width) and the slide
     (height) while preserving aspect ratio. */
  /* Don't force vertical centering here — image rows set align-items:center in their own inline
     style, while two-text-column rows want their headers top-aligned (default stretch). */
  .reveal section > div[style*="flex"] > div { flex: 1 1 0; min-width: 0; }
  .reveal section > div[style*="flex"] > p,
  .reveal section > div[style*="flex"] > img { flex: 0 0 auto; min-width: 0; margin: 0; max-width: 48%; }
  .reveal section > div[style*="flex"] p { margin: 0; }
  .reveal section > div[style*="flex"] img {
    max-height: 58vh; max-width: 100%; width: auto; height: auto; object-fit: contain; margin: 0;
  }
  .reveal .credit { font-size: 12pt; color: #666; }
  .reveal .small { font-size: 12pt; color: #666; }
  .reveal .ref { font-size: 11pt; color: #888; }
  .reveal .cvline { font-size: 14pt; margin: 9px 0; line-height: 1.4; }
  .reveal .chip { display: inline-block; font-size: 10pt; font-weight: 700; padding: 2px 9px;
                  border-radius: 999px; margin-right: 8px; color: #fff; vertical-align: middle; }
  .reveal .c-cert { background: #6b7785; }
  .reveal .c-ref  { background: #2166ac; }
  .reveal .c-can  { background: #b8860b; }
  .reveal .muted  { color: #8a8a8a; }
  .reveal .doi { color:#2166ac; font-size:11pt; }
  .reveal a.demo { color:#1b7837; font-weight:600; font-size:14pt; text-decoration:none; border-bottom:1px solid #9fcbb0; }
  /* Markdown tables (Marp source uses these instead of hand-built HTML tables). */
  .reveal table { border-collapse: collapse; font-size: 13pt; margin: 10px 0; }
  .reveal th, .reveal td { border: 1px solid #dcdfe4; padding: 6px 9px; text-align: left; vertical-align: top; }
  .reveal th { background: #eef1f5; color: #1b2a4a; }
  .reveal code { font-size: .9em; background: #f1f4f8; padding: 1px 6px; border-radius: 4px; }
  .deck { position:fixed; top:0; left:0; right:0; bottom:0; }
  .deck .reveal { width:100%; height:100%; }
</style>
</head>
<body>
<div class="deck">
<div class="reveal">
  <div class="slides">
<!--SLIDES-->
  </div>
</div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.1.0/reveal.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.1.0/plugin/notes/notes.min.js"></script>
<script>
  Reveal.initialize({ hash: true, slideNumber: "c/t", plugins: [ RevealNotes ] });
</script>
</body>
</html>
"""

md = markdown.Markdown(extensions=["extra", "sane_lists", "md_in_html"])

# Marp parses markdown inside HTML blocks (the flex/grid column <div>s); python-markdown only
# does so for tags carrying a `markdown` attribute. Inject it into every opening <div>.
DIV_RE = re.compile(r"<div\b")

STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
CLASS_RE = re.compile(r"<!--\s*_class:\s*([\w-]+)\s*-->")
COMMENT_RE = re.compile(r"<!--(.*?)-->", re.DOTALL)
IMG_RE = re.compile(r"<img\b([^>]*?)/?>", re.IGNORECASE)
ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
SIZE_RE = re.compile(r"^([hw]):(\d+)$")


def size_images(html):
    """Turn Marp `![h:340](x)` (rendered by markdown as <img alt="h:340" src="x">) into a
    sized image. Raw <img> tags authored directly in the .md (with their own height/style
    attributes) are left untouched — only the Marp size token is translated."""
    def repl(m):
        attrs = dict(ATTR_RE.findall(m.group(1)))
        sm = SIZE_RE.match(attrs.get("alt", "").strip())
        if not sm:
            return m.group(0)  # not a Marp size image — preserve the tag verbatim
        dim = "height" if sm.group(1) == "h" else "width"
        return f'<img src="{attrs.get("src", "")}" alt="" style="{dim}:{sm.group(2)}px">'
    return IMG_RE.sub(repl, html)


def render_slide(raw):
    notes = []
    # `_class:` directive first (it is also a comment), then collect the rest as speaker notes.
    cm = CLASS_RE.search(raw)
    cls = CLASS_MAP.get(cm.group(1), "") if cm else ""
    raw = CLASS_RE.sub("", raw)
    raw = STYLE_RE.sub("", raw)
    for c in COMMENT_RE.findall(raw):
        c = c.strip()
        if c:
            notes.append(c)
    raw = COMMENT_RE.sub("", raw).strip()
    raw = DIV_RE.sub('<div markdown="1"', raw)

    md.reset()
    body = size_images(md.convert(raw))
    aside = f'\n      <aside class="notes">{" ".join(notes)}</aside>' if notes else ""
    opening = f'<section class="{cls}">' if cls else "<section>"
    return f"    {opening}\n      {body}{aside}\n    </section>"


def main():
    text = open(SRC, encoding="utf-8").read().replace(IMG_FROM, IMG_TO)

    # Source hygiene — catch edits that silently break rendering (an indented '---' is not
    # recognized as a slide break; unbalanced <div> tags swallow following content).
    indented_sep = re.findall(r"(?m)^[ \t]+---[ \t]*$", text)
    opens, closes = text.count("<div"), text.count("</div>")
    if indented_sep:
        print(f"  WARNING: {len(indented_sep)} indented '---' — not treated as a slide break; "
              f"move to column 0")
    if opens != closes:
        print(f"  WARNING: unbalanced <div>: {opens} open vs {closes} close — a slide's layout "
              f"div is likely unclosed")

    parts = re.split(r"(?m)^---$", text)
    # parts[0] = leading comment, parts[1] = YAML frontmatter, parts[2:] = slides.
    slides = [render_slide(p) for p in parts[2:] if p.strip()]
    html = TEMPLATE.replace("<!--SLIDES-->", "\n\n".join(slides))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(html)

    # Sanity checks — surface anything the parser did not fully translate.
    leftovers = {
        "unconverted ![...] images": html.count("!["),
        "leaked _class directives": len(CLASS_RE.findall(html)),
        "unrewritten ../../ paths": html.count("../../"),
    }
    with_notes = sum(1 for s in slides if "<aside" in s)
    print(f"wrote {OUT}: {len(slides)} slides, {with_notes} with speaker notes")
    for k, v in leftovers.items():
        if v:
            print(f"  WARNING: {v} {k}")


if __name__ == "__main__":
    main()

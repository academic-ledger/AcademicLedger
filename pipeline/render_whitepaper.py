"""Render docs/QaL_whitepaper.md -> web/public/whitepaper.html (served on-site, like talk.html).

Re-run whenever the white paper changes:  python pipeline/render_whitepaper.py
"""
import os
import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "docs", "QaL_whitepaper.md")
OUT = os.path.join(ROOT, "web", "public", "whitepaper.html")

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'"
           "%3E%3Crect width='100' height='100' rx='22' fill='%23111'/%3E%3Ctext x='51' y='70' "
           "text-anchor='middle' fill='white' font-family='Georgia,serif' font-size='58'%3E"
           "%3Ctspan font-style='italic'%3Ea%3C/tspan%3E%3Ctspan%3EL%3C/tspan%3E%3C/text%3E%3C/svg%3E")

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>White paper — How QaL Works · academic Ledger</title>
<link rel="icon" href="{favicon}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&display=swap" rel="stylesheet">
<style>
  :root{{ --navy:#16243d; --green:#2e8b57; --ink:#1c2433; --muted:#6b7280; --line:#e7e9ee; --bg:#fafbfc; }}
  *{{box-sizing:border-box;}}
  html,body{{margin:0; background:var(--bg); color:var(--ink); line-height:1.62;
            font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}}
  a{{color:#2166ac; text-decoration:none;}} a:hover{{text-decoration:underline;}}
  .brand{{background:#fff; border-bottom:1px solid var(--line); padding:11px 22px; display:flex; align-items:center; justify-content:space-between;}}
  .brand .left{{display:flex; align-items:center; gap:13px;}}
  .brand .lock{{display:inline-flex; align-items:center; gap:11px; text-decoration:none;}}
  .brand .al{{width:30px; height:30px; border-radius:22%; background:#111; color:#fff; display:inline-flex; align-items:center; justify-content:center; font-family:"Cormorant Garamond",Georgia,serif; font-weight:600; font-size:21px; line-height:1;}}
  .brand .al .i{{font-style:italic; font-weight:500;}}
  .brand .nm{{font-family:"Cormorant Garamond",Garamond,serif; font-size:25px; line-height:1;}}
  .brand .nm .ac{{font-style:italic; font-weight:400; color:#555; font-size:.95em;}}
  .brand .nm .le{{font-weight:500; color:#111;}}
  .brand .nav a{{color:var(--muted); margin-left:15px; font-size:13px;}}
  .brand .nav a.on{{color:#111; font-weight:600;}}
  .wrap{{max-width:820px; margin:0 auto; padding:34px 24px 90px;}}
  .wrap h1{{font-size:34px; line-height:1.15; color:var(--navy); margin:6px 0 6px; font-weight:700;}}
  .wrap h2{{font-family:"Cormorant Garamond",Georgia,serif; font-size:26px; color:var(--navy); font-weight:600; margin:36px 0 10px; padding-top:8px; border-top:1px solid var(--line);}}
  .wrap h3{{font-size:16px; color:var(--navy); margin:24px 0 6px;}}
  .wrap p, .wrap li{{font-size:16px;}}
  .wrap em{{color:#33415a;}}
  code{{background:#f1f4f8; padding:1px 5px; border-radius:4px; font-size:.92em;}}
  pre{{background:#f7f9fb; border:1px solid var(--line); border-radius:8px; padding:12px 14px; overflow-x:auto;}}
  blockquote{{border-left:3px solid var(--green); background:#f4f8f5; margin:16px 0; padding:10px 16px; color:#26344b; border-radius:0 8px 8px 0;}}
  table{{border-collapse:collapse; width:100%; font-size:14.5px; margin:14px 0; display:block; overflow-x:auto;}}
  th,td{{border:1px solid var(--line); padding:7px 10px; text-align:left; vertical-align:top;}}
  th{{background:#f4f6f8; color:#3a4250; font-weight:700;}}
  hr{{border:none; border-top:1px solid var(--line); margin:26px 0;}}
  footer{{color:#9aa3af; font-size:12px; border-top:1px solid var(--line); margin-top:40px; padding-top:14px;}}
  @media(max-width:600px){{ .brand{{flex-wrap:wrap; gap:8px 12px; padding:10px 16px;}} .brand .nav a{{margin-left:0; margin-right:14px;}} .wrap{{padding-left:16px; padding-right:16px;}} }}
</style>
</head>
<body>
<header class="brand">
  <div class="left">
    <a class="lock" href="/" title="academic Ledger"><span class="al"><span class="i">a</span>L</span>
      <span class="nm"><span class="ac">academic</span><span class="le">Ledger</span></span></a>
  </div>
  <nav class="nav"><a href="/explore">Explore</a><a href="/author">Author</a><a href="/about">About</a><a href="/talk.html">Talk</a></nav>
</header>
<div class="wrap">
{body}
<footer>academic Ledger · methodology white paper, rendered from <a href="https://github.com/ktulrich/AcademicLedger/blob/main/docs/QaL_whitepaper.md">docs/QaL_whitepaper.md</a>. Research preview; worked single-paper values are illustrative pending calibration.</footer>
</div>
</body>
</html>
"""


def main():
    md = open(SRC, encoding="utf-8").read()
    body = markdown.markdown(md, extensions=["extra", "sane_lists", "toc"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(TEMPLATE.format(favicon=FAVICON, body=body))
    print(f"wrote {OUT} ({len(body)} chars of body)")


if __name__ == "__main__":
    main()

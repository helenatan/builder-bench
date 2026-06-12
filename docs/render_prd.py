#!/usr/bin/env python3
"""Render docs/PRD.md to a self-contained, readable docs/PRD.html.

Usage: python docs/render_prd.py   (re-run whenever PRD.md changes)
Needs: pip install markdown
"""
from __future__ import annotations

import re
from pathlib import Path

import markdown

HERE = Path(__file__).parent
SRC = HERE / "PRD.md"
OUT = HERE / "PRD.html"
REPO_BLOB = "https://github.com/helenatan/builder-bench/blob/main"

CSS = """
:root {
  --bg: #fdfdfb; --fg: #1d1d1f; --muted: #59595e; --accent: #0a5dc2;
  --border: #e3e2dd; --soft: #f4f3ee; --th: #ece9e2; --zebra: #f8f7f3;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16181d; --fg: #e8e8ea; --muted: #a0a0a8; --accent: #6cb0ff;
    --border: #33363e; --soft: #1f2229; --th: #262a32; --zebra: #1b1e24;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font: 17px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
}
main { max-width: 56rem; margin: 0 auto; padding: 2.5rem 1.5rem 6rem; }
h1 { font-size: 2rem; line-height: 1.25; margin: 0 0 .4rem; letter-spacing: -.01em; }
h1 + p strong { font-weight: 600; color: var(--muted); }
h2 {
  font-size: 1.45rem; margin: 3rem 0 1rem; padding-bottom: .35rem;
  border-bottom: 2px solid var(--border); letter-spacing: -.01em;
}
h3 { font-size: 1.12rem; margin: 2rem 0 .75rem; }
h4 { font-size: 1rem; margin: 1.5rem 0 .5rem; }
p, ul, ol { margin: .8rem 0; }
li { margin: .35rem 0; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
hr { border: none; border-top: 1px solid var(--border); margin: 2.5rem 0; }
del { color: var(--muted); }
blockquote {
  margin: 1.2rem 0; padding: .8rem 1.1rem; background: var(--soft);
  border-left: 4px solid var(--accent); border-radius: 0 6px 6px 0;
}
blockquote p { margin: .4rem 0; }
code {
  font: .88em/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: var(--soft); border: 1px solid var(--border);
  border-radius: 4px; padding: .08em .35em;
}
pre { background: var(--soft); border: 1px solid var(--border);
      border-radius: 8px; padding: 1rem; overflow-x: auto; }
pre code { background: none; border: none; padding: 0; }

.table-wrap { overflow-x: auto; margin: 1.2rem 0; border: 1px solid var(--border);
              border-radius: 8px; }
table { border-collapse: collapse; width: 100%; font-size: .88rem; line-height: 1.5; }
th, td { padding: .6rem .75rem; text-align: left; vertical-align: top;
         border-bottom: 1px solid var(--border); }
th { background: var(--th); font-weight: 650; position: sticky; top: 0; }
tr:nth-child(even) td { background: var(--zebra); }
tr:last-child td { border-bottom: none; }
td:not(:last-child), th:not(:last-child) { border-right: 1px solid var(--border); }
/* wide tables (the §5 master table) get room and a minimum width to stay legible */
.table-wrap.wide table { min-width: 1080px; }

.toc { background: var(--soft); border: 1px solid var(--border); border-radius: 8px;
       padding: 1rem 1.4rem; margin: 1.6rem 0 2.4rem; }
.toc::before { content: "Contents"; font-weight: 650; display: block; margin-bottom: .4rem; }
.toc ul { list-style: none; margin: 0; padding: 0; columns: 2; column-gap: 2.5rem; }
.toc ul ul { display: none; }            /* top-level sections only */
.toc li { margin: .2rem 0; break-inside: avoid; }
@media (max-width: 640px) { .toc ul { columns: 1; } body { font-size: 16px; } }
@media print {
  body { background: #fff; color: #000; font-size: 11pt; }
  .table-wrap { overflow: visible; border: none; }
  .table-wrap.wide table { min-width: 0; }
  .toc { display: none; }
}
"""


def main() -> None:
    text = SRC.read_text()

    # ~~strikethrough~~ -> <del> (not covered by the 'extra' extension)
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text, flags=re.S)

    # table of contents placeholder after the front-matter block (first ---)
    text = text.replace("---\n\n## 1.", "[TOC]\n\n## 1.", 1)

    html = markdown.markdown(text, extensions=["extra", "toc"],
                             extension_configs={"toc": {"toc_depth": "2"}})

    # rewrite relative .md links so they work from the standalone HTML file
    def fix_link(m: re.Match) -> str:
        href = m.group(1)
        path = ("docs/" + href) if not href.startswith("../") else href[3:]
        return f'href="{REPO_BLOB}/{path}"'
    html = re.sub(r'href="(?!https?://|#)([^"]+\.md)"', fix_link, html)

    # wrap tables for horizontal scrolling; tag 5+ column tables as wide
    def wrap_table(m: re.Match) -> str:
        tbl = m.group(0)
        cols = tbl.split("</tr>", 1)[0].count("<th>")
        cls = "table-wrap wide" if cols >= 5 else "table-wrap"
        return f'<div class="{cls}">{tbl}</div>'
    html = re.sub(r"<table>.*?</table>", wrap_table, html, flags=re.S)

    OUT.write_text(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Builder-Bench: PRD</title>
<style>{CSS}</style>
</head>
<body>
<main>
{html}
</main>
</body>
</html>
""")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()

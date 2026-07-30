#!/usr/bin/env python3
"""Render Mike's rocket-equations notebook to a read-only static HTML page.

Verbatim render: markdown prose (as Jupyter markdown, math left as raw
LaTeX for client-side MathJax), code cells with their execution prompts,
and saved outputs (stream text, execute_result, and embedded PNG images)
in original cell order. Nothing is summarized, reordered, or invented.
"""

from __future__ import annotations

import base64
import html
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SOURCE_NOTEBOOK = Path("/home/cgl/dev/rocketry/rocket equations.ipynb")
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "web/toys/mike-rocketry-notebook"


def source_of_truth_note() -> str:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%H %aI"],
            cwd=str(SOURCE_NOTEBOOK.parent),
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return f"last committed {out}" if out else "not under version control here"
    except Exception:
        return "version info unavailable"


def commit_hash_note() -> str:
    try:
        h = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(SOURCE_NOTEBOOK.parent),
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", SOURCE_NOTEBOOK.name],
            cwd=str(SOURCE_NOTEBOOK.parent), capture_output=True, text=True, check=True,
        ).stdout.strip()
        note = " (working tree has uncommitted changes to this file)" if dirty else ""
        return f"{h[:12]}{note}"
    except Exception:
        return "unavailable"


def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    # **bold** before single-asterisk *italic*, so italic's negative
    # lookaround doesn't have to fight bold's doubled markers.
    text = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def render_table(rows: list[str]) -> str:
    def cells_of(row: str) -> list[str]:
        return [c.strip() for c in row.strip().strip("|").split("|")]

    header = cells_of(rows[0])
    body_rows = [cells_of(r) for r in rows[2:]]  # rows[1] is the --- separator
    thead = "<tr>" + "".join(f"<th>{inline(c)}</th>" for c in header) + "</tr>"
    tbody = "\n".join(
        "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body_rows
    )
    return f'<div class="md-table-wrap"><table><thead>{thead}</thead><tbody>{tbody}</tbody></table></div>'


def render_markdown(src: str) -> str:
    """Literal markdown -> HTML: headers, paragraphs, bold/italic, unordered
    and ordered lists, pipe tables. Leaves $...$ / $$...$$ untouched for
    MathJax."""
    lines = src.split("\n")
    out: list[str] = []
    para: list[str] = []

    def flush_para():
        if not para:
            return
        text = " ".join(para).strip()
        if text:
            out.append(f"<p>{inline(text)}</p>")
        para.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        stripped = line.strip()

        if stripped and re.fullmatch(r"=+", nxt.strip() or ""):
            flush_para()
            out.append(f"<h2>{inline(stripped)}</h2>")
            i += 2
            continue
        if stripped and re.fullmatch(r"-{2,}", nxt.strip() or ""):
            flush_para()
            out.append(f"<h3>{inline(stripped)}</h3>")
            i += 2
            continue

        if stripped.startswith("|"):
            flush_para()
            table_lines = []
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                table_lines.append(lines[j])
                j += 1
            if len(table_lines) >= 2 and re.fullmatch(r"\|?[\s:|-]+\|?", table_lines[1].strip()):
                out.append(render_table(table_lines))
                i = j
                continue

        is_bullet = re.match(r"^[-*]\s+\S", stripped)
        is_ordered = re.match(r"^\d+\.\s+\S", stripped)
        if is_bullet or is_ordered:
            flush_para()
            marker_re = r"^[-*]\s+" if is_bullet else r"^\d+\.\s+"
            item_start_re = r"^[-*]\s+\S" if is_bullet else r"^\d+\.\s+\S"
            items = []
            j = i
            while j < len(lines) and re.match(item_start_re, lines[j].strip()):
                item_text = [re.sub(marker_re, "", lines[j].strip())]
                j += 1
                # lazy continuation: fold following non-blank, non-new-item
                # lines into the same bullet (source wraps bullets across
                # several physical lines)
                while j < len(lines) and lines[j].strip() and not re.match(item_start_re, lines[j].strip()):
                    item_text.append(lines[j].strip())
                    j += 1
                items.append(" ".join(item_text))
            tag = "ul" if is_bullet else "ol"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(it)}</li>" for it in items) + f"</{tag}>")
            i = j
            continue

        if stripped == "":
            flush_para()
        else:
            para.append(line)
        i += 1
    flush_para()
    return "\n".join(out)


def render_output(o: dict) -> str:
    ot = o.get("output_type")
    if ot == "stream":
        text = "".join(o.get("text", []))
        return f'<pre class="output stream">{html.escape(text)}</pre>'
    if ot in ("execute_result", "display_data"):
        data = o.get("data", {})
        if "image/png" in data:
            b64 = data["image/png"]
            if isinstance(b64, list):
                b64 = "".join(b64)
            prefix = ""
            if ot == "execute_result" and o.get("execution_count") is not None:
                prefix = f'<div class="prompt out-prompt">Out[{o["execution_count"]}]:</div>'
            return f'{prefix}<img class="output image" alt="notebook output figure" src="data:image/png;base64,{b64}">'
        if "text/plain" in data:
            text = data["text/plain"]
            if isinstance(text, list):
                text = "".join(text)
            prefix = ""
            if ot == "execute_result" and o.get("execution_count") is not None:
                prefix = f'<div class="prompt out-prompt">Out[{o["execution_count"]}]:</div>'
            return f'{prefix}<pre class="output result">{html.escape(text)}</pre>'
    if ot == "error":
        text = "\n".join(o.get("traceback", []))
        return f'<pre class="output error">{html.escape(text)}</pre>'
    return ""


CAPTAIN_MARK = "▸ Captain"  # matches the notebook's own "▸ Captain" section-heading tag


def render_cell(index: int, cell: dict) -> str:
    ctype = cell["cell_type"]
    src = "".join(cell.get("source", []))
    tag = f'<span class="captain-tag">{CAPTAIN_MARK}</span>' if CAPTAIN_MARK in src else ""
    if ctype == "markdown":
        return f'<div class="cell markdown" id="cell-{index}">{tag}{render_markdown(src)}</div>'
    if ctype == "code":
        exec_count = cell.get("execution_count")
        prompt = f"In [{exec_count}]:" if exec_count is not None else "In [ ]:"
        code_html = html.escape(src)
        outputs_html = "\n".join(render_output(o) for o in cell.get("outputs", []))
        outputs_block = f'<div class="outputs">{outputs_html}</div>' if outputs_html else ""
        return (
            f'<div class="cell code" id="cell-{index}">'
            f'{tag}'
            f'<div class="prompt in-prompt">{prompt}</div>'
            f'<pre class="input"><code>{code_html}</code></pre>'
            f"{outputs_block}"
            f"</div>"
        )
    return ""


def build_toc(nb_cells: list[dict]) -> str:
    """Table of contents from every H2-level (====) markdown header, in order."""
    items = []
    for i, c in enumerate(nb_cells):
        if c["cell_type"] != "markdown":
            continue
        src = "".join(c.get("source", []))
        lines = src.split("\n")
        for j, line in enumerate(lines):
            nxt = lines[j + 1].strip() if j + 1 < len(lines) else ""
            if line.strip() and re.fullmatch(r"=+", nxt):
                title = line.strip()
                is_captain = CAPTAIN_MARK in title
                label = title.replace(f"— {CAPTAIN_MARK}", "").replace(CAPTAIN_MARK, "").strip(" —-")
                items.append(f'<li><a href="#cell-{i}">{html.escape(label)}</a>{" <span class=\"toc-tag\">▸</span>" if is_captain else ""}</li>')
                break
    return "<ol class=\"toc-list\">" + "\n".join(items) + "</ol>"


def extract_section(nb_cells: list[dict], heading_startswith: str) -> str:
    """Render just one markdown cell's body (sans its own H2, already shown
    via the section wrapper) by matching the start of its heading text."""
    for c in nb_cells:
        if c["cell_type"] != "markdown":
            continue
        src = "".join(c.get("source", []))
        if src.strip().startswith(heading_startswith):
            body = render_markdown(src)
            body = re.sub(r"^<h2>.*?</h2>\n?", "", body, count=1)
            return body
    raise ValueError(f"section not found: {heading_startswith!r}")


def extract_output_text(nb_cells: list[dict], contains: str) -> str:
    for c in nb_cells:
        if c["cell_type"] != "code":
            continue
        if contains not in "".join(c.get("source", [])):
            continue
        parts = []
        for o in c.get("outputs", []):
            if o.get("output_type") == "stream":
                parts.append("".join(o.get("text", [])))
        if parts:
            return "".join(parts)
    raise ValueError(f"output not found for cell containing: {contains!r}")


def main() -> None:
    nb = json.loads(SOURCE_NOTEBOOK.read_text())
    cells = nb["cells"]
    cells_html = "\n".join(render_cell(i, c) for i, c in enumerate(cells))
    toc_html = build_toc(cells)

    # Front-page summary blocks are extracted verbatim from the notebook's
    # own Abstract / Assumptions / Results / Limitations sections -- not
    # re-authored here -- so the landing page can't drift from the source.
    abstract_html = extract_section(cells, "Abstract and precise question")
    results_html = extract_section(cells, "Results summary")
    limitations_html = extract_section(cells, "Limitations & open questions")
    assumptions_text = extract_output_text(cells, "## Assumptions block")

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    source_mtime = datetime.fromtimestamp(
        SOURCE_NOTEBOOK.stat().st_mtime, timezone.utc
    ).replace(microsecond=0).isoformat()
    version_note = source_of_truth_note()
    commit_note = commit_hash_note()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE_NOTEBOOK, OUTPUT_DIR / "rocket-equations.ipynb")

    page = TEMPLATE.format(
        cells=cells_html,
        toc=toc_html,
        abstract=abstract_html,
        results=results_html,
        limitations=limitations_html,
        assumptions=html.escape(assumptions_text),
        generated_at=generated_at,
        source_mtime=source_mtime,
        version_note=html.escape(version_note),
        commit_note=html.escape(commit_note),
        cell_count=len(cells),
    )
    (OUTPUT_DIR / "index.html").write_text(page)
    print(f"wrote {OUTPUT_DIR / 'index.html'} ({len(cells)} cells)")


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Read-only static render of Mike's actual rocket-equations notebook, verbatim, cell by cell.">
  <title>Rocket Equations — Mike's Notebook (Read-Only) · Fleet Monad</title>
  <link rel="stylesheet" href="styles.css">
  <script>
    window.MathJax = {{
      tex: {{ inlineMath: [['$', '$']], displayMath: [['$$', '$$']] }}
    }};
  </script>
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" defer></script>
</head>
<body>
  <header class="masthead">
    <a class="back" href="../../index.html">&larr; Fleet Monad</a>
    <span class="sep">&middot;</span>
    <a class="back" href="../mike-rocketry/">Mike's Variable-Exhaust Rocket Lab</a>
    <div class="eyebrow">Read-only render &middot; NEW</div>
    <h1>Rocket Equations &mdash; Mike's Notebook</h1>
    <p class="sourced">
      Static, verbatim render of <code>rocket equations.ipynb</code> ({cell_count} cells),
      preserving Mike's original prose, math, code, outputs, and cell order.
      Nothing here is summarized or reinterpreted &mdash; that reading lives in the
      adjacent <a href="../mike-rocketry/">interactive reverie</a> instead.
    </p>
    <p class="meta">
      Source notebook last modified <code>{source_mtime}</code> ({version_note}).
      Repo commit <code>{commit_note}</code>.
      This page rendered <code>{generated_at}</code>.
      <a href="rocket-equations.ipynb" download>Download the .ipynb</a>
    </p>
  </header>

  <section class="frontmatter">
    <div class="fm-col fm-abstract">
      <h2>Abstract</h2>
      {abstract}
    </div>
    <div class="fm-col fm-toc">
      <h2>Contents</h2>
      {toc}
    </div>
  </section>

  <section class="frontmatter">
    <div class="fm-col">
      <h2>Assumptions summary</h2>
      <pre class="assumptions-pre">{assumptions}</pre>
      <p class="fm-note">Full editable assumptions block is in the notebook body below.</p>
    </div>
    <div class="fm-col">
      <h2>Key results</h2>
      {results}
    </div>
  </section>

  <section class="frontmatter frontmatter-full">
    <div class="fm-col">
      <h2>Open questions</h2>
      {limitations}
    </div>
  </section>

  <main class="notebook">
{cells}
  </main>
  <footer class="foot">Read-only render. Edits happen in the source notebook, not here.</footer>
</body>
</html>
"""

if __name__ == "__main__":
    main()

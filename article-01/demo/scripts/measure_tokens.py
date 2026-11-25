"""Experiment A: token counts of the same screen spec in several input representations.

Writes every representation to demo/representations/ (so anyone can re-count them
with another tokenizer) and the counts to research/token-results.csv.

Tokenizers: tiktoken o200k_base and cl100k_base (public, offline after the first
download). Claude counts come from scripts/claude_token_count.mjs, which writes
research/claude-token-counts.json; when that file exists its numbers are merged in.

Usage (from demo/):  scripts/.venv/Scripts/python scripts/measure_tokens.py
"""

from __future__ import annotations

import csv
import json
import re
import zipfile
from importlib.metadata import version
from pathlib import Path

import tiktoken
from markitdown import MarkItDown
from openpyxl import load_workbook

DEMO = Path(__file__).resolve().parent.parent
OUT = DEMO / "representations"
RESEARCH = DEMO.parent / "research"
ENCODINGS = ["o200k_base", "cl100k_base"]


def xlsx_structured(path: Path) -> str:
    """Our own minimal extractor: one block per sheet, one line per row, non-empty cells joined by ' | '.
    Merged cells keep their value in the top-left cell only (openpyxl default)."""
    wb = load_workbook(path, data_only=True)
    out = []
    for ws in wb.worksheets:
        out.append(f"## シート: {ws.title}")
        for row in ws.iter_rows():
            cells = [str(c.value).replace("\n", " / ") for c in row if c.value is not None and str(c.value).strip() != ""]
            if cells:
                out.append(" | ".join(cells))
        out.append("")
    return "\n".join(out)


def xlsx_raw_xml(path: Path) -> str:
    """Reference only: every XML part of the .xlsx package, as an agent would see it after unzipping."""
    with zipfile.ZipFile(path) as z:
        return "\n".join(f"<!-- {n} -->\n" + z.read(n).decode("utf-8") for n in sorted(z.namelist()) if n.endswith(".xml") or n.endswith(".rels"))


def strip_blocks(src: str, tag: str) -> str:
    return re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>\s*", "", src, flags=re.S)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    md = MarkItDown()
    html_src = (DEMO / "order_design.html").read_text(encoding="utf-8")
    preview = (DEMO / "templates" / "preview.html").read_text(encoding="utf-8").strip()
    assert preview in html_src, "preview partial not found verbatim in order_design.html"
    css = "\n".join(re.findall(r"<style\b[^>]*>.*?</style>", html_src, flags=re.S))
    js = "\n".join(re.findall(r"<script\b[^>]*>.*?</script>", html_src, flags=re.S))
    no_css_js = strip_blocks(strip_blocks(html_src, "style"), "script")
    spec_only = no_css_js.replace(preview, "")

    reps = [
        # (id, format, representation, text, note)
        ("xlsx_structured", "Excel", "Structured text (openpyxl, own extractor)", xlsx_structured(DEMO / "order_design.xlsx"), "1 line per row, cells joined by ' | ', 1 block per sheet"),
        ("xlsx_markitdown", "Excel", "Markdown via MarkItDown", md.convert(str(DEMO / "order_design.xlsx")).text_content, f"markitdown {version('markitdown')} (pandas → HTML → Markdown)"),
        ("md_raw", "Markdown", "Raw Markdown", (DEMO / "order_design.md").read_text(encoding="utf-8"), "headings + pipe tables + text wireframe"),
        ("html_raw", "HTML", "Raw HTML (full file)", html_src, "includes CSS, JS and the interactive preview"),
        ("html_no_css_js", "HTML", "HTML without <style>/<script>", no_css_js, "markup of spec tables + preview form"),
        ("html_spec_only", "HTML", "HTML spec tables only", spec_only, "also without the preview form markup"),
        ("html_markitdown", "HTML", "Markdown via MarkItDown", md.convert(str(DEMO / "order_design.html")).text_content, f"markitdown {version('markitdown')} (markdownify)"),
        ("html_spec_nolinks", "HTML (variant)", "HTML spec tables only, ID links unwrapped", re.sub(r'<a href="#[^"]+">([^<]*)</a>', r"\1", spec_only), "shows what the cross-reference links cost"),
        ("html_css_only", "HTML (part)", "CSS only", css, "component of html_raw"),
        ("html_js_only", "HTML (part)", "JavaScript only", js, "component of html_raw"),
        ("html_preview_only", "HTML (part)", "Preview form markup only", preview, "component of html_raw"),
        ("json_source", "Reference", "JSON source (order_spec.json)", (DEMO / "spec" / "order_spec.json").read_text(encoding="utf-8"), "single source the three files are generated from"),
        ("xlsx_raw_xml", "Reference", "Unzipped .xlsx XML parts", xlsx_raw_xml(DEMO / "order_design.xlsx"), "not a realistic input; shows why a parser is needed"),
    ]

    claude_path = RESEARCH / "claude-token-counts.json"
    claude = json.loads(claude_path.read_text(encoding="utf-8")) if claude_path.exists() else {}
    claude_model = claude.get("model", "")
    claude_counts = claude.get("counts", {})

    encs = {e: tiktoken.get_encoding(e) for e in ENCODINGS}
    rows = []
    for rid, fmt, rep, text, note in reps:
        (OUT / f"{rid}.txt").write_text(text, encoding="utf-8", newline="\n")
        row = {
            "id": rid,
            "format": fmt,
            "representation": rep,
            "chars": len(text),
            "utf8_bytes": len(text.encode("utf-8")),
            **{e: len(encs[e].encode(text, disallowed_special=())) for e in ENCODINGS},
            "claude_tokens": claude_counts.get(rid, ""),
            "claude_model": claude_model if rid in claude_counts else "",
            "note": note,
        }
        rows.append(row)

    base = next(r for r in rows if r["id"] == "md_raw")
    for r in rows:
        r["o200k_vs_md"] = f"{r['o200k_base'] / base['o200k_base']:.2f}"
    RESEARCH.mkdir(exist_ok=True)
    with (RESEARCH / "token-results.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"tiktoken {version('tiktoken')}, markitdown {version('markitdown')}, openpyxl {version('openpyxl')}")
    print(f"{'id':18} {'chars':>7} {'o200k':>7} {'cl100k':>7} {'claude':>7} {'vs md':>6}")
    for r in rows:
        print(f"{r['id']:18} {r['chars']:>7} {r['o200k_base']:>7} {r['cl100k_base']:>7} {str(r['claude_tokens']):>7} {r['o200k_vs_md']:>6}")


if __name__ == "__main__":
    main()

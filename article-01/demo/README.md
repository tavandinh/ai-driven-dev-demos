# Demo: 受注登録画面 (SCR-ORD-001) in Excel, Markdown and HTML

Demo for article 01 of the series 「AI駆動開発を実践する」. The business rules are fictional and exist only for this article.

## Files

| Path | What it is |
|---|---|
| `spec/order_spec.json` | The single source: overview, areas, items, events, validations, business rules, messages, UI states, test data |
| `order_design.xlsx` | Excel spec, 10 sheets in Japanese SIer style (generated) |
| `order_design.md` | Markdown spec (generated) |
| `order_design.html` | HTML spec with an interactive screen preview; open it directly in a browser, no server or network needed (generated) |
| `templates/` | HTML shell (CSS + JS) and preview markup used to build `order_design.html` |
| `scripts/` | Build, equivalence check, token measurement, Experiment B, Git diff demo, screenshots |
| `tests/order_design.spec.mjs` | 20 Playwright tests of the preview (named after the spec IDs they exercise) |
| `embed/index.html` | Embed-friendly view for Qiita (screen first, spec tables below), built by `scripts/build_embed.py` from the same `build_html()` output; not a benchmark input |
| `tests/embed.spec.mjs` | 6 local checks of the embed page (same tables and script as the full spec, BR-002 flow, small widths) |
| `screenshots/` | PNG images for the article (real captures from Excel and Chromium) |

All three spec files are generated from the JSON, so they carry the same business information (`check_equivalence.py` checks that all 600 JSON values are present in each file; a presence check, not proof of semantic equivalence). Do not edit the generated files by hand; edit the JSON or the templates and rebuild.

## Requirements

- Python 3.12 with a venv: `python -m venv scripts/.venv` then `scripts/.venv/Scripts/python -m pip install -r scripts/requirements.txt` (on macOS/Linux, `scripts/.venv/bin/python`).
- Node 22+ and the repository's dependencies (`@playwright/test` 1.64.1, `@anthropic-ai/claude-agent-sdk` 0.3.325), installed at the repository root.
- For the Claude measurements only: a logged-in Claude Code (the scripts use the Claude Agent SDK; they cost money, see below).
- For Excel screenshots only: Windows with Microsoft Excel.

## Commands

Run from this `demo/` folder unless noted. On Windows set `PYTHONIOENCODING=utf-8` first.

```bash
PY=scripts/.venv/Scripts/python

$PY scripts/build_specs.py          # build .md / .xlsx / .html from the JSON
$PY scripts/build_embed.py          # build embed/index.html (fails if order_design.html is stale)
$PY scripts/check_equivalence.py    # every JSON value present in every format (exit 1 if not)
$PY scripts/measure_tokens.py       # Experiment A: tiktoken counts → ../research/token-results.csv
$PY scripts/git_diff_demo.py <empty-dir> > ../research/git-diff-demo.txt   # change-management demo
```

From the repository root:

```bash
D=article-01/demo
node node_modules/@playwright/test/cli.js test -c $D/playwright.config.mjs    # 20 + 6 browser tests
node $D/scripts/capture_html_screenshots.mjs                                  # HTML screenshots
node $D/scripts/claude_token_count.mjs            # Claude token counts (≈ US$0.03, Haiku)
$D/scripts/.venv/Scripts/python $D/scripts/measure_tokens.py   # merge the Claude column
node $D/scripts/experiment_b.mjs <empty-dir-outside-repo> 5     # Experiment B (≈ US$0.17, Haiku)
```

Excel screenshots (Windows PowerShell, Excel installed):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/capture_excel_screenshots.ps1
```

The Excel script hides the ribbon and the formula bar (they show the user's add-ins and account) and restores them afterwards. Check the first image before publishing it.

## Versions used for the published numbers (2026-11-25)

Python 3.12.10, openpyxl 3.1.5, tiktoken 0.14.0, markitdown 0.1.9, pandas 3.1.1; Node 22.16.0, @playwright/test 1.64.1 (Chromium), @anthropic-ai/claude-agent-sdk 0.3.325, model `claude-haiku-5-5`; Windows 11, Microsoft Excel (Microsoft 365).

## What the preview does and does not do

It implements every validation (VR-01–VR-19), business rules BR-001–BR-007, the events and the six UI states, reading messages, master data and rule parameters (`data-*` on the rule rows) from the spec tables in the same file. The review bar (login user switch, sample data, ID overlay, event log) is a review aid, not part of the specification. BR-003 is checked in the UI only; real authorization belongs on the server, which this demo does not have. No data is sent anywhere.

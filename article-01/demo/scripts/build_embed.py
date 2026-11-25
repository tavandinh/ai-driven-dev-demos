"""Build embed/index.html: an embed-friendly view of order_design.html for Qiita (CodeSandbox).

The embed page is NOT a second implementation. It is the exact output of
build_specs.build_html() (same spec tables, same preview markup, same CSS/JS),
with presentation-only changes:
- the document header and table of contents are hidden, and the screen preview
  (section 3) is moved to the top, so readers can try it without scrolling;
- a one-line hint (threshold read from BR-002 in order_spec.json) sits above the
  preview; the disclaimer moves below the preview, before the spec tables;
- the review controls (仕様外) are regrouped: sample buttons first, the
  「高額（承認あり）」 button highlighted, the login-user select and the ID overlay
  checkbox in a collapsible 「その他の操作」 panel. The original elements (same ids,
  same data attributes) are moved, not rewritten, so the unchanged script binds to them;
- embed-only CSS: line items shown as cards on narrow screens, larger touch
  targets, no nested scroll box for the event log.

The business script, the spec tables and every rule stay byte-identical to
order_design.html (tests/embed.spec.mjs checks this).

All spec tables stay in the page below the preview, because the preview reads
its messages, masters and rule parameters from them, and the ID links jump to them.

This script does not write order_design.* (the measured benchmark inputs). It
checks that build_html() still reproduces order_design.html byte for byte, so the
embed page cannot drift from the published spec.

Usage (from demo/):  scripts/.venv/Scripts/python scripts/build_embed.py
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_specs as bs  # noqa: E402

NARROW = "(max-width: 599px)"

EMBED_CSS = """
      /* ---- embed view (build_embed.py): presentation only ---- */
      .embed .doc-header, .embed nav.toc { display: none; }
      .embed .layout { display: block; }
      .embed main { display: flex; flex-direction: column; padding: 8px; }
      .embed main > section { min-width: 0; }
      .embed #layout { order: -1; padding: 8px; }
      .embed #h-layout { display: none; }
      .embed-intro { background: var(--accent); color: #fff; padding: 5px 10px; font-size: 13px; line-height: 1.45; }
      .embed-intro p { margin: 0; }
      .embed-intro small { font-size: 11px; opacity: 0.85; }
      .embed-note { margin: 12px 0; padding: 6px 10px; border-left: 3px solid var(--line); color: var(--muted); font-size: 12px; }

      /* review controls (仕様外) */
      .embed .review-bar { display: grid; grid-template-columns: minmax(0, 1fr); gap: 6px; padding: 6px 8px; margin-bottom: 8px; }
      .embed-bar-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 2px 8px; }
      .embed .sample-group { display: grid; grid-template-columns: 1fr 1.7fr 1fr; gap: 6px; }
      .embed .sample-label { grid-column: 1 / -1; color: var(--muted); }
      .embed .sample-group button { min-height: 40px; padding: 4px 6px; border: 1px solid #9aa5b1; border-radius: 6px; background: #fff; color: var(--ink); font-size: 13px; white-space: normal; line-height: 1.25; transition: background-color 0.15s, border-color 0.15s; }
      .embed .sample-group button:hover { background: var(--accent-soft); border-color: var(--accent); }
      .embed .sample-group button:active { transform: translateY(1px); }
      .embed .sample-group button[data-sample="approval"] { border: 2px solid var(--accent); color: var(--accent); font-weight: bold; }
      .embed .sample-group button[aria-pressed="true"] { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: bold; }
      .embed .sample-group button[aria-pressed="true"]::before { content: "✓ "; }
      .embed-sample-status { margin: 0; padding: 4px 8px; border-radius: 4px; background: var(--ok-soft); color: var(--ok); font-size: 12px; }
      .embed-sample-status:empty { display: none; }
      @keyframes embed-flash { from { box-shadow: 0 0 0 4px #f0b400; } to { box-shadow: 0 0 0 4px rgba(240, 180, 0, 0); } }
      .embed .embed-flash { animation: embed-flash 1.8s ease-out; border-radius: 8px; }
      .embed-options summary { cursor: pointer; color: var(--accent); padding: 2px 0; }
      .embed-options[open] summary { margin-bottom: 4px; }
      .embed-options label { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; margin: 4px 0; white-space: normal; }
      .embed-options select { min-height: 34px; }

      /* the event log grows with the page instead of scrolling inside the iframe */
      .embed .event-log ol { max-height: none; overflow: visible; }

      @media NARROW {
        .embed main, .embed #layout { padding: 4px; }
        .embed #layout { border: 0; background: none; }
        .embed form { padding: 10px 10px 12px; }
        .embed fieldset { padding: 6px 10px 10px; }
        .embed .field label, .embed .field .label { font-size: 13px; }
        .embed .req { font-size: 11px; }
        .embed input, .embed select, .embed textarea { font-size: 16px; min-height: 40px; }
        .embed .scr-buttons button { flex: 1 1 0; min-height: 44px; }
        /* line items as cards: same cells, labels drawn by CSS (with item IDs when the ID overlay is on) */
        .embed table.lines { min-width: 0; }
        .embed table.lines thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
        .embed table.lines, .embed table.lines tbody { display: block; }
        .embed table.lines tr { display: block; border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; margin-bottom: 8px; background: #fff; }
        .embed table.lines td { display: grid; grid-template-columns: 9em minmax(0, 1fr); align-items: center; gap: 0 8px; border: 0; padding: 3px 0 !important; text-align: left; }
        .embed table.lines td::before { font-size: 12px; font-weight: bold; color: var(--muted); }
        .embed table.lines td .field-error { grid-column: 2; }
        .embed table.lines td.no { display: block; font-weight: bold; text-align: left; width: auto; }
        .embed table.lines td.no::before { content: "明細 "; color: var(--ink); font-size: inherit; }
        .embed table.lines td:nth-child(2)::before { content: "商品コード（必須）"; }
        .embed table.lines td:nth-child(3)::before { content: "商品名"; }
        .embed table.lines td:nth-child(4)::before { content: "数量（必須）"; }
        .embed table.lines td:nth-child(5)::before { content: "単価"; }
        .embed table.lines td:nth-child(6)::before { content: "金額"; }
        .embed .show-ids table.lines td:nth-child(2)::before { content: "商品コード（必須）ITM-08"; }
        .embed .show-ids table.lines td:nth-child(3)::before { content: "商品名 ITM-09"; }
        .embed .show-ids table.lines td:nth-child(4)::before { content: "数量（必須）ITM-10"; }
        .embed .show-ids table.lines td:nth-child(5)::before { content: "単価 ITM-11"; }
        .embed .show-ids table.lines td:nth-child(6)::before { content: "金額 ITM-12"; }
        .embed table.lines input.code, .embed table.lines input.qty { width: 100%; max-width: 180px; }
        .embed table.lines td:last-child { display: block; text-align: right; }
      }
""".replace("NARROW", NARROW)


# Embed-only UI feedback for the sample buttons. It is a separate script that runs after
# the business script (which fills the form on the same click) and only reads the result:
# it marks the pressed button, says what happened, and scrolls to the part that changed.
EMBED_UI_JS = """    <script>
      // Embed-only UI feedback (build_embed.py). No business logic: the business script above
      // fills the form on the same click; this only shows which sample is active and where to look.
      (() => {
        const $ = (s) => document.querySelector(s);
        const buttons = [...document.querySelectorAll(".sample-group [data-sample]")];
        const status = $("#embed-sample-status");
        const screen = $("#screen");
        const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        const total = () => $("#f-total").textContent.trim();
        const feedback = {
          normal: () => [$("#btn-confirm").closest(".scr-buttons"), `「通常」を入力しました（合計 ${total()} 円）。そのまま［確認］を押せます。`],
          approval: () => [$("#f-approver").closest("fieldset"), `「高額（承認あり）」を入力しました（合計 ${total()} 円）。承認者が必須になり、選ぶまで［確認］は押せません。`],
          error: () => [$(".field-error:not(:empty)")?.closest("fieldset") || screen, "「エラー」を入力しました。各項目の下にエラーが表示されます。"],
        };
        const press = (key) => buttons.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.sample === key)));
        press(null);
        for (const b of buttons) {
          b.addEventListener("click", () => {
            const key = b.dataset.sample;
            press(key);
            const [target, text] = feedback[key]();
            status.textContent = text;
            target.classList.remove("embed-flash");
            void target.offsetWidth;
            target.classList.add("embed-flash");
            target.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "center" });
          });
        }
        // Back to the initial state (クリア / 新規受注): no sample is active any more.
        new MutationObserver(() => {
          if (screen.dataset.state === "ST-01") {
            press(null);
            status.textContent = "";
          }
        }).observe(screen, { attributes: true, attributeFilter: ["data-state"] });
      })();
    </script>
"""


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"expected exactly one {old!r} in the generated HTML")
    return text.replace(old, new)


def take(pattern: str, text: str) -> str:
    found = re.findall(pattern, text, flags=re.S)
    if len(found) != 1:
        raise SystemExit(f"expected exactly one match for {pattern!r}")
    return found[0]


def regroup_review_bar(out: str) -> str:
    """Move the original review controls into a compact layout (no control is rewritten)."""
    bar = take(r'<div class="review-bar"[^>]*>.*?</div>', out)
    tag = take(r'<span class="review-tag">.*?</span>', bar)
    user = take(r"<label\s*>ログインユーザー.*?</label>", bar)
    ids = take(r'<label class="check">.*?</label>', bar)
    buttons = re.findall(r'<button type="button" data-sample="[a-z]+">.*?</button>', bar)
    if [re.search(r'data-sample="([a-z]+)"', b).group(1) for b in buttons] != ["normal", "approval", "error"]:
        raise SystemExit("unexpected sample buttons in the review bar")
    state = take(r'<span class="state-indicator">.*?</span>', bar)
    new_bar = (
        '<div class="review-bar" role="group" aria-label="レビュー用操作（仕様外）">\n'
        f'    <div class="embed-bar-head">{tag}{state}</div>\n'
        '    <div class="sample-group" role="group" aria-label="サンプル入力">\n'
        '      <span class="sample-label">サンプル入力</span>\n      '
        + "\n      ".join(buttons)
        + "\n    </div>\n"
        '    <p id="embed-sample-status" class="embed-sample-status" role="status" aria-live="polite"></p>\n'
        '    <details class="embed-options">\n'
        "      <summary>その他の操作（ログインユーザー・ID表示）</summary>\n"
        f"      {user}\n      {ids}\n"
        "    </details>\n"
        "  </div>"
    )
    return replace_once(out, bar, new_bar)


def build_embed(full: str) -> str:
    m = bs.META
    br002 = next(r for r in bs.SPEC["businessRules"] if r["id"] == "BR-002")
    threshold = bs.yen(br002["params"]["threshold"])
    intro = (
        '<div class="embed-intro">\n'
        "  <p>「高額（承認あり）」を押して、承認者が必須になる動きを確認してみてください。"
        f"<br /><small>数量を変えて {threshold} 円以上にしても同じ（架空のデモ）</small></p>\n"
        "</div>\n"
    )
    note = (
        f'<p class="embed-note">ここから下は {html.escape(m["documentTitle"])}（{html.escape(m["screenId"])}）の仕様表です。'
        f"ID をクリックすると定義へ移動します。{html.escape(m['disclaimer'])}</p>\n"
    )
    out = replace_once(full, '<html lang="ja">', '<html lang="ja" class="embed">')
    out = replace_once(
        out,
        f"<title>{html.escape(m['documentTitle'])}（{html.escape(m['screenId'])}）</title>",
        f"<title>{html.escape(m['documentTitle'])}（{html.escape(m['screenId'])}）埋め込み版</title>",
    )
    out = replace_once(out, "    </style>\n  </head>", EMBED_CSS + "    </style>\n  </head>")
    out = replace_once(out, "  <body>\n", "  <body>\n" + intro)
    out = regroup_review_bar(out)
    out = replace_once(out, "<h3>領域一覧</h3>", note + "<h3>領域一覧</h3>")
    out = replace_once(out, "  </body>\n</html>", EMBED_UI_JS + "  </body>\n</html>")
    return out


def main() -> None:
    template = (bs.DEMO / "templates" / "order_design.template.html").read_text(encoding="utf-8")
    full = bs.build_html(template)
    published = (bs.DEMO / "order_design.html").read_text(encoding="utf-8")
    if full != published:
        raise SystemExit("order_design.html differs from build_html(); run build_specs.py first")
    out_dir = bs.DEMO / "embed"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "index.html").write_text(build_embed(full), encoding="utf-8", newline="\n")
    print("built: embed/index.html (from the same build_html() output as order_design.html)")


if __name__ == "__main__":
    main()

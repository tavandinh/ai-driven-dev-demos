"""Build embed/index.html: an embed-friendly view of order_design.html for Qiita (CodeSandbox).

The embed page is NOT a second implementation. It is the exact output of
build_specs.build_html() (same spec tables, same preview markup, same CSS/JS),
with three presentation changes:
- the document header and table of contents are hidden;
- the screen preview (section 3) is moved to the top, so readers can try it
  without scrolling through the document;
- a short hint line (threshold read from BR-002 in order_spec.json) and the
  disclaimer are shown above the preview.

All spec tables stay in the page below the preview, because the preview reads
its messages, masters and rule parameters from them, and the ID links jump to them.

This script does not write order_design.* (the measured benchmark inputs). It
checks that build_html() still reproduces order_design.html byte for byte, so the
embed page cannot drift from the published spec.

Usage (from demo/):  scripts/.venv/Scripts/python scripts/build_embed.py
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_specs as bs  # noqa: E402

EMBED_CSS = """
      /* ---- embed view (build_embed.py) ---- */
      .embed .doc-header, .embed nav.toc { display: none; }
      .embed .layout { display: block; }
      .embed main { display: flex; flex-direction: column; padding: 8px; }
      .embed main > section { min-width: 0; }
      .embed #layout { order: -1; padding: 8px; }
      .embed #h-layout { display: none; }
      .embed-intro { background: var(--accent); color: #fff; padding: 6px 12px; font-size: 13px; line-height: 1.5; }
      .embed-intro p { margin: 0; }
      .embed-intro .embed-note { opacity: 0.85; font-size: 11px; }
"""


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"expected exactly one {old!r} in the generated HTML")
    return text.replace(old, new)


def build_embed(full: str) -> str:
    m = bs.META
    br002 = next(r for r in bs.SPEC["businessRules"] if r["id"] == "BR-002")
    threshold = bs.yen(br002["params"]["threshold"])
    intro = (
        '<div class="embed-intro">\n'
        f"  <p>「高額（承認あり）」を押すか、数量を変えて合計（税込）を {threshold} 円以上にしてみてください。"
        "承認者が必須になり、選ぶまで［確認］は押せません（BR-002）。</p>\n"
        f"  <p class=\"embed-note\">{html.escape(m['documentTitle'])}（{html.escape(m['screenId'])}）の画面プレビュー。"
        f"下に仕様書の表が続きます（ID をクリックで移動）。{html.escape(m['disclaimer'])}</p>\n"
        "</div>\n"
    )
    out = replace_once(full, '<html lang="ja">', '<html lang="ja" class="embed">')
    out = replace_once(
        out,
        f"<title>{html.escape(m['documentTitle'])}（{html.escape(m['screenId'])}）</title>",
        f"<title>{html.escape(m['documentTitle'])}（{html.escape(m['screenId'])}）埋め込み版</title>",
    )
    out = replace_once(out, "    </style>\n  </head>", EMBED_CSS + "    </style>\n  </head>")
    out = replace_once(out, "  <body>\n", "  <body>\n" + intro)
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

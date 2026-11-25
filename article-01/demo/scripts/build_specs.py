"""Build order_design.md / .xlsx / .html from one neutral source (spec/order_spec.json).

All three outputs carry the same business information. Only the presentation differs:
- Markdown: headings + tables.
- Excel: one sheet per section, Japanese SIer style (header block, borders,
  a 方眼紙 wireframe on the layout sheet).
- HTML: the same tables + an interactive screen preview (template + CSS/JS).

Usage (from demo/):  scripts/.venv/Scripts/python scripts/build_specs.py
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

DEMO = Path(__file__).resolve().parent.parent
SPEC = json.loads((DEMO / "spec" / "order_spec.json").read_text(encoding="utf-8"))
META = SPEC["meta"]
ITEMS = {i["id"]: i for i in SPEC["items"]}

# ---------------------------------------------------------------- shared table model
# Each section: (anchor, number + title, header, rows). Every format renders these.


def item_label(item_id: str) -> str:
    return f"{item_id} {ITEMS[item_id]['name']}"


def yen(value: str) -> str:
    return f"{int(value):,}"


def sections() -> list[dict]:
    m = META
    return [
        {
            "id": "overview",
            "title": "1. 概要",
            "header": ["項目", "内容"],
            "rows": [
                ["システム名", m["system"]],
                ["画面ID", m["screenId"]],
                ["画面名", m["screenName"]],
                ["版数", m["version"]],
                ["更新日", m["updated"]],
                ["作成者", m["author"]],
                ["目的", m["purpose"]],
                ["利用者", m["actors"]],
                ["遷移元", m["entry"]],
                ["凡例", m["legend"]],
            ],
        },
        {
            "id": "revisions",
            "title": "2. 改訂履歴",
            "header": ["版数", "日付", "作成者", "内容"],
            "rows": [[r["version"], r["date"], r["author"], r["description"]] for r in SPEC["revisions"]],
        },
        {
            "id": "layout",
            "title": "3. 画面レイアウト",
            "header": ["領域ID", "領域名", "配置", "含まれる項目", "説明"],
            "rows": [[a["id"], a["name"], a["position"], a["items"], a["description"]] for a in SPEC["areas"]],
            "rowIds": [a["id"] for a in SPEC["areas"]],
        },
        {
            "id": "items",
            "title": "4. 項目定義",
            "header": ["No", "項目ID", "領域", "項目名", "入出力", "型", "桁数", "必須", "初期値", "形式・制約", "関連"],
            "rows": [
                [str(n), i["id"], i["area"], i["name"], i["io"], i["type"], i["length"], i["required"], i["default"], i["format"], i["related"]]
                for n, i in enumerate(SPEC["items"], 1)
            ],
            "rowIds": [i["id"] for i in SPEC["items"]],
        },
        {
            "id": "events",
            "title": "5. イベント定義",
            "header": ["イベントID", "イベント名", "契機", "条件", "処理内容", "遷移先"],
            "rows": [[e["id"], e["name"], e["trigger"], e["condition"], e["steps"], e["next"]] for e in SPEC["events"]],
            "rowIds": [e["id"] for e in SPEC["events"]],
        },
        {
            "id": "validations",
            "title": "6. 入力チェック",
            "header": ["チェックID", "対象項目", "チェック内容", "エラー条件", "タイミング", "メッセージID", "業務ルール"],
            "rows": [[v["id"], item_label(v["item"]), v["check"], v["error"], v["timing"], v["message"], v["rule"]] for v in SPEC["validations"]],
            "rowIds": [v["id"] for v in SPEC["validations"]],
            "params": [v.get("params", {}) for v in SPEC["validations"]],
        },
        {
            "id": "rules",
            "title": "7. 業務ルール",
            "header": ["ルールID", "ルール名", "内容", "備考", "関連"],
            "rows": [[b["id"], b["name"], b["rule"], b["note"], b["related"]] for b in SPEC["businessRules"]],
            "rowIds": [b["id"] for b in SPEC["businessRules"]],
            "params": [b.get("params", {}) for b in SPEC["businessRules"]],
        },
        {
            "id": "messages",
            "title": "8. メッセージ",
            "header": ["メッセージID", "種別", "メッセージ", "パラメータ"],
            "rows": [[x["id"], x["type"], x["text"], x["params"]] for x in SPEC["messages"]],
            "rowIds": [x["id"] for x in SPEC["messages"]],
            "textCol": 2,
        },
        {
            "id": "states",
            "title": "9. 画面状態",
            "header": ["状態ID", "状態名", "表示", "ボタン", "遷移"],
            "rows": [[s["id"], s["name"], s["display"], s["buttons"], s["transitions"]] for s in SPEC["states"]],
            "rowIds": [s["id"] for s in SPEC["states"]],
        },
    ]


def test_data_tables() -> list[dict]:
    td = SPEC["testData"]
    return [
        {"id": "td-customers", "title": "10.1 顧客マスタ", "header": ["顧客コード", "顧客名", "取引状態"], "rows": [[c["code"], c["name"], c["status"]] for c in td["customers"]]},
        {"id": "td-products", "title": "10.2 商品マスタ", "header": ["商品コード", "商品名", "単価（円）"], "rows": [[p["code"], p["name"], yen(p["price"])] for p in td["products"]]},
        {"id": "td-users", "title": "10.3 社員", "header": ["社員コード", "氏名", "役割"], "rows": [[u["code"], u["name"], u["role"]] for u in td["users"]]},
    ]


# ---------------------------------------------------------------- Markdown


def md_cell(value) -> str:
    if isinstance(value, list):
        return "<br>".join(f"{n}. {s}" for n, s in enumerate(value, 1))
    return str(value).replace("|", "\\|") if value != "" else ""


def md_table(header: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(md_cell(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


# Text wireframe for Markdown. Same labels and notes as the Excel 方眼紙 drawing.
MD_WIREFRAME = """\
[A-01 ヘッダー] 受注登録　　　　　　　　　　ITM-01 ログインユーザー：山田 太郎（U001）
[A-02 メッセージ] （エラー件数・エラー一覧、登録完了メッセージを表示）
[A-03 受注基本情報]
  ITM-02 受注番号 [ORD-YYYYMMDD-NNNN]　　ITM-03 受注日 ○ [YYYY-MM-DD]
  ITM-04 顧客コード ○ [      ]　　　　　　ITM-05 顧客名 [          ]
  ITM-06 希望納期 ○ [YYYY-MM-DD]　　　　ITM-07 支払条件 ○ [▼ 選択してください]
[A-04 受注明細]
  No | ITM-08 商品コード ○ | ITM-09 商品名 | ITM-10 数量 ○ | ITM-11 単価 | ITM-12 金額 | BTN-02
  1  | [      ]            |               | [ ]           |             |             | [行削除]
  2  | [      ]            |               | [ ]           |             |             | [行削除]
  [行追加] BTN-01　明細は1〜5行。単価・商品名は商品マスタから表示
[A-05 金額集計]　ITM-13 小計 [0]　ITM-14 消費税 [0]　ITM-15 合計金額（税込） [0]
[A-06 承認情報]　ITM-16 承認者 △ [▼ 選択してください]　△：合計金額（税込）1,000,000円以上で必須（BR-002）
[A-07 備考]　ITM-17 備考 [（200文字以内）]
[A-08 ボタン]　　　　　　　　　　　　　　[クリア] BTN-03　[確認] BTN-04
  確認画面（ST-04）：[戻る] BTN-05　[登録] BTN-06　／　登録完了（ST-06）：[新規受注] BTN-07"""


def build_md() -> str:
    parts = [f"# {META['documentTitle']}（{META['screenId']}）", "", f"> {META['disclaimer']}", ""]
    for s in sections():
        if s["id"] == "layout":
            parts += [f"## {s['title']}", "", "```text", MD_WIREFRAME, "```", "", "### 領域一覧", "", md_table(s["header"], s["rows"]), ""]
            continue
        parts += [f"## {s['title']}", "", md_table(s["header"], s["rows"]), ""]
    parts += ["## 10. テストデータ", ""]
    for t in test_data_tables():
        parts += [f"### {t['title']}", "", md_table(t["header"], t["rows"]), ""]
    return "\n".join(parts)


# ---------------------------------------------------------------- Excel

FONT = "Meiryo UI"
THIN = Side(style="thin", color="808080")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEAD_FILL = PatternFill("solid", fgColor="DDEBF7")
LABEL_FILL = PatternFill("solid", fgColor="F2F2F2")
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)

COL_WIDTHS = {
    "overview": [16, 90],
    "revisions": [8, 12, 12, 50],
    "layout": [8, 14, 18, 30, 50],
    "items": [5, 9, 7, 16, 8, 11, 6, 6, 14, 40, 26],
    "events": [11, 14, 22, 22, 60, 16],
    "validations": [11, 18, 14, 36, 10, 13, 11],
    "rules": [10, 18, 60, 40, 22],
    "messages": [13, 8, 60, 26],
    "states": [9, 12, 50, 34, 28],
}
SHEET_NAMES = {
    "overview": "表紙",
    "revisions": "改訂履歴",
    "items": "項目定義",
    "events": "イベント定義",
    "validations": "入力チェック",
    "rules": "業務ルール",
    "messages": "メッセージ",
    "states": "画面状態",
}


def style(cell, *, bold=False, fill=None, align=WRAP, border=True, size=10):
    cell.font = Font(name=FONT, size=size, bold=bold)
    cell.alignment = align
    if fill:
        cell.fill = fill
    if border:
        cell.border = BORDER


def header_block(ws, title: str, col_spans: list[int]) -> None:
    """Row 1: the document header every sheet of a Japanese 設計書 repeats. Row 2: sheet title."""
    pairs = [("システム名", META["system"]), ("画面ID", META["screenId"]), ("画面名", META["screenName"]), ("版数", META["version"]), ("更新日", META["updated"]), ("作成者", META["author"])]
    col = 1
    for (label, value), (lw, vw) in zip(pairs, zip(col_spans[0::2], col_spans[1::2])):
        for text, width, fill in ((label, lw, LABEL_FILL), (value, vw, None)):
            if width > 1:
                ws.merge_cells(start_row=1, start_column=col, end_row=1, end_column=col + width - 1)
            for c in range(col, col + width):
                style(ws.cell(row=1, column=c), fill=fill, align=CENTER, size=9)
            ws.cell(row=1, column=col, value=text)
            col += width
    t = ws.cell(row=2, column=1, value=title)
    t.font = Font(name=FONT, size=12, bold=True)
    ws.row_dimensions[2].height = 22


def table_sheet(wb: Workbook, key: str, title: str, header: list[str], rows: list[list]) -> None:
    ws = wb.create_sheet(SHEET_NAMES[key])
    widths = COL_WIDTHS[key]
    for n, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(n)].width = w
    header_line(ws, title, len(widths))
    if key == "overview":
        ws.cell(row=3, column=1, value=META["disclaimer"]).font = Font(name=FONT, size=9, italic=True)
    start = 4
    for c, h in enumerate(header, 1):
        style(ws.cell(row=start, column=c, value=h), bold=True, fill=HEAD_FILL, align=CENTER)
    for r, row in enumerate(rows, start + 1):
        for c, v in enumerate(row, 1):
            if isinstance(v, list):
                v = "\n".join(f"{n}. {s}" for n, s in enumerate(v, 1))
            elif v.isdigit():
                v = int(v)  # No, 桁数, 初期値: numbers, not text
            style(ws.cell(row=r, column=c, value=v))
    ws.freeze_panes = ws.cell(row=start + 1, column=1)
    page_setup(ws)


def header_line(ws, title: str, ncols: int) -> None:
    """Table sheets: the same document header as one bordered line across the table width."""
    text = "　".join(
        f"{k}：{v}"
        for k, v in (("システム名", META["system"]), ("画面ID", META["screenId"]), ("画面名", META["screenName"]), ("版数", META["version"]), ("更新日", META["updated"]), ("作成者", META["author"]))
    )
    if ncols > 1:
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    for c in range(1, ncols + 1):
        style(ws.cell(row=1, column=c), fill=LABEL_FILL, align=Alignment(vertical="center"), size=9)
    ws.cell(row=1, column=1, value=text)
    t = ws.cell(row=2, column=1, value=title)
    t.font = Font(name=FONT, size=12, bold=True)
    ws.row_dimensions[2].height = 22


def page_setup(ws) -> None:
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def layout_sheet(wb: Workbook) -> None:
    """画面レイアウト: a 方眼紙 wireframe (48 narrow columns) plus the area table."""
    ws = wb.create_sheet("画面レイアウト")
    W = 48
    for c in range(1, W + 1):
        ws.column_dimensions[get_column_letter(c)].width = 2.9
    header_block(ws, "3. 画面レイアウト", [4, 7, 3, 5, 3, 5, 2, 2, 3, 4, 3, 7])
    ws.row_dimensions[1].height = 30

    def merge(r1, c1, r2, c2, value=None, *, bold=False, fill=None, align=CENTER, border=True, size=9):
        if (r1, c1) != (r2, c2):
            ws.merge_cells(start_row=r1, start_column=c1, end_row=r2, end_column=c2)
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                style(ws.cell(row=r, column=c), bold=bold, fill=fill, align=align, border=border, size=size)
        if value is not None:
            # Sample numbers ("0", "1") are stored as numbers, not text.
            ws.cell(row=r1, column=c1, value=int(value) if isinstance(value, str) and value.isdigit() else value)

    def frame(r1, r2, area_id):
        """Outline an area box and write its title in the top-left corner."""
        thick = Side(style="medium", color="1F4E79")
        for r in range(r1, r2 + 1):
            for c in range(1, W + 1):
                cell = ws.cell(row=r, column=c)
                b = cell.border
                cell.border = Border(
                    left=thick if c == 1 else b.left,
                    right=thick if c == W else b.right,
                    top=thick if r == r1 else b.top,
                    bottom=thick if r == r2 else b.bottom,
                )
        area = next(a for a in SPEC["areas"] if a["id"] == area_id)
        t = ws.cell(row=r1, column=1, value=f"{area_id} {area['name']}")
        t.font = Font(name=FONT, size=9, bold=True, color="1F4E79")

    def field(r, c, item_id, width_label, width_box, sample="", mark=None):
        req = ITEMS[item_id]["required"] if mark is None else mark
        label = f"{item_id} {ITEMS[item_id]['name']}" + (f" {req}" if req else "")
        merge(r, c, r, c + width_label - 1, label, fill=LABEL_FILL, align=Alignment(vertical="center", wrap_text=True))
        merge(r, c + width_label, r, c + width_label + width_box - 1, sample, align=Alignment(vertical="center"))

    # A-01 ヘッダー
    frame(4, 6, "A-01")
    merge(5, 2, 5, 16, "受注登録", bold=True, border=False, size=12, align=Alignment(vertical="center"))
    merge(5, 30, 5, 47, "ITM-01 ログインユーザー：山田 太郎（U001）", border=False, align=Alignment(horizontal="right", vertical="center"))
    # A-02 メッセージ
    frame(7, 9, "A-02")
    merge(8, 2, 8, 47, "（エラー件数・エラー一覧、登録完了メッセージを表示）", border=False)
    # A-03 受注基本情報
    frame(10, 14, "A-03")
    field(11, 2, "ITM-02", 8, 12, "ORD-YYYYMMDD-NNNN")
    field(11, 25, "ITM-03", 8, 12, "YYYY-MM-DD")
    field(12, 2, "ITM-04", 8, 12)
    field(12, 25, "ITM-05", 8, 15)
    field(13, 2, "ITM-06", 8, 12, "YYYY-MM-DD")
    field(13, 25, "ITM-07", 8, 15, "▼ 選択してください")
    # A-04 受注明細
    frame(15, 21, "A-04")
    cols = [("No", 2), ("ITM-08 商品コード ○", 7), ("ITM-09 商品名", 13), ("ITM-10 数量 ○", 5), ("ITM-11 単価", 6), ("ITM-12 金額", 7), ("BTN-02", 4)]
    c = 2
    for name, w in cols:
        merge(16, c, 16, c + w - 1, name, bold=True, fill=HEAD_FILL)
        for r, n in ((17, "1"), (18, "2")):
            merge(r, c, r, c + w - 1, n if name == "No" else ("[行削除]" if name == "BTN-02" else ""))
        c += w
    merge(20, 2, 20, 8, "[行追加] BTN-01", fill=LABEL_FILL)
    merge(20, 10, 20, 47, "明細は1〜5行。単価・商品名は商品マスタから表示", border=False, align=Alignment(vertical="center"))
    # A-05 金額集計
    frame(22, 26, "A-05")
    for r, item_id in ((23, "ITM-13"), (24, "ITM-14"), (25, "ITM-15")):
        field(r, 28, item_id, 10, 9, "0")
    # A-06 承認情報
    frame(27, 29, "A-06")
    field(28, 2, "ITM-16", 10, 15, "▼ 選択してください")
    merge(28, 29, 28, 47, "△：合計金額（税込）1,000,000円以上で必須（BR-002）", border=False, align=Alignment(vertical="center"))
    # A-07 備考
    frame(30, 33, "A-07")
    merge(31, 2, 32, 8, "ITM-17 備考", fill=LABEL_FILL)
    merge(31, 9, 32, 47, "（200文字以内）", align=Alignment(vertical="top"))
    # A-08 ボタン
    frame(34, 37, "A-08")
    merge(35, 30, 35, 37, "[クリア] BTN-03", fill=LABEL_FILL)
    merge(35, 39, 35, 47, "[確認] BTN-04", fill=LABEL_FILL)
    merge(36, 2, 36, 47, "確認画面（ST-04）：[戻る] BTN-05　[登録] BTN-06　／　登録完了（ST-06）：[新規受注] BTN-07", border=False, align=Alignment(horizontal="right", vertical="center"))

    # Area table under the wireframe.
    s = next(x for x in sections() if x["id"] == "layout")
    r0 = 40
    ws.cell(row=r0 - 1, column=1, value="領域一覧").font = Font(name=FONT, size=10, bold=True)
    spans = [4, 6, 7, 12, 19]
    c = 1
    for h, w in zip(s["header"], spans):
        merge(r0, c, r0, c + w - 1, h, bold=True, fill=HEAD_FILL)
        c += w
    for i, row in enumerate(s["rows"], 1):
        c = 1
        for v, w in zip(row, spans):
            merge(r0 + i, c, r0 + i, c + w - 1, v, align=WRAP)
            c += w
        ws.row_dimensions[r0 + i].height = 30
    page_setup(ws)


def build_xlsx(path: Path) -> None:
    wb = Workbook()
    wb.remove(wb.active)
    secs = {s["id"]: s for s in sections()}
    for key in ("overview", "revisions"):
        s = secs[key]
        title = f"{META['documentTitle']}（{META['screenId']}）　{s['title']}" if key == "overview" else s["title"]
        table_sheet(wb, key, title, s["header"], s["rows"])
    layout_sheet(wb)
    for key in ("items", "events", "validations", "rules", "messages", "states"):
        s = secs[key]
        table_sheet(wb, key, s["title"], s["header"], s["rows"])
    # Test data: three tables on one sheet.
    ws = wb.create_sheet("テストデータ")
    for n, w in enumerate([14, 28, 14], 1):
        ws.column_dimensions[get_column_letter(n)].width = w
    header_line(ws, "10. テストデータ", 3)
    r = 4
    for t in test_data_tables():
        ws.cell(row=r, column=1, value=t["title"]).font = Font(name=FONT, size=10, bold=True)
        r += 1
        for c, h in enumerate(t["header"], 1):
            style(ws.cell(row=r, column=c, value=h), bold=True, fill=HEAD_FILL, align=CENTER)
        for row in t["rows"]:
            r += 1
            for c, v in enumerate(row, 1):
                cell = ws.cell(row=r, column=c)
                if t["id"] == "td-products" and c == 3:
                    cell.value = int(v.replace(",", ""))
                    cell.number_format = "#,##0"
                else:
                    cell.value = v
                style(cell)
        r += 2
    page_setup(ws)
    wb.save(path)


# ---------------------------------------------------------------- HTML

ID_RE = re.compile(r"\b(ITM-\d{2}|BTN-\d{2}|EV-\d{2}|VR-\d{2}|BR-\d{3}|MSG-[EIQ]\d{3}|ST-\d{2}|A-\d{2})\b")


def linkify(text: str, own_id: str | None = None) -> str:
    def repl(m: re.Match) -> str:
        ref = m.group(1)
        return ref if ref == own_id else f'<a href="#{ref}">{ref}</a>'

    return ID_RE.sub(repl, html.escape(text, quote=False))


def html_table(s: dict) -> str:
    row_ids = s.get("rowIds")
    params = s.get("params")
    head = "".join(f"<th scope=\"col\">{html.escape(h)}</th>" for h in s["header"])
    body = []
    for n, row in enumerate(s["rows"]):
        own = row_ids[n] if row_ids else None
        attrs = f' id="{own}"' if own else ""
        if params and params[n]:
            attrs += "".join(f' data-{re.sub(r"([A-Z])", r"-\1", k).lower()}="{html.escape(v)}"' for k, v in params[n].items())
        cells = []
        for c, v in enumerate(row):
            if isinstance(v, list):
                inner = "<ol>" + "".join(f"<li>{linkify(x, own)}</li>" for x in v) + "</ol>"
            else:
                inner = linkify(v, own)
            cls = ' class="msg-text"' if s.get("textCol") == c else ""
            tag = "th" if c == 0 and own else "td"
            scope = ' scope="row"' if tag == "th" else ""
            cells.append(f"<{tag}{scope}{cls}>{inner}</{tag}>")
        body.append(f"<tr{attrs}>" + "".join(cells) + "</tr>")
    return (
        f'<div class="table-wrap"><table id="tbl-{s["id"]}">\n<thead><tr>{head}</tr></thead>\n<tbody>\n'
        + "\n".join(body)
        + "\n</tbody>\n</table></div>"
    )


def build_html(template: str) -> str:
    out = []
    for s in sections():
        if s["id"] == "layout":
            # The live preview sits right before the area table.
            out.append('<section id="layout" aria-labelledby="h-layout">\n<h2 id="h-layout">3. 画面レイアウト</h2>\n<!--PREVIEW-->\n<h3>領域一覧</h3>\n' + html_table(s) + "\n</section>")
            continue
        out.append(f'<section id="{s["id"]}" aria-labelledby="h-{s["id"]}">\n<h2 id="h-{s["id"]}">{html.escape(s["title"])}</h2>\n{html_table(s)}\n</section>')
    td = ['<section id="testdata" aria-labelledby="h-testdata">\n<h2 id="h-testdata">10. テストデータ</h2>']
    for t in test_data_tables():
        td.append(f"<h3>{html.escape(t['title'])}</h3>\n{html_table(t)}")
    td.append("</section>")
    out.append("\n".join(td))
    body = "\n\n".join(out)
    preview = (DEMO / "templates" / "preview.html").read_text(encoding="utf-8")
    body = body.replace("<!--PREVIEW-->", preview.strip())
    m = META
    return (
        template.replace("{{TITLE}}", html.escape(f"{m['documentTitle']}（{m['screenId']}）"))
        .replace("{{DOC_TITLE}}", html.escape(m["documentTitle"]))
        .replace("{{SYSTEM}}", html.escape(m["system"]))
        .replace("{{SCREEN_ID}}", html.escape(m["screenId"]))
        .replace("{{VERSION}}", html.escape(m["version"]))
        .replace("{{UPDATED}}", html.escape(m["updated"]))
        .replace("{{DISCLAIMER}}", html.escape(m["disclaimer"]))
        .replace("<!--SECTIONS-->", body)
    )


def main() -> None:
    (DEMO / "order_design.md").write_text(build_md(), encoding="utf-8", newline="\n")
    build_xlsx(DEMO / "order_design.xlsx")
    template = (DEMO / "templates" / "order_design.template.html").read_text(encoding="utf-8")
    (DEMO / "order_design.html").write_text(build_html(template), encoding="utf-8", newline="\n")
    print("built: order_design.md, order_design.xlsx, order_design.html")


if __name__ == "__main__":
    main()

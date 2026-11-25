"""Check that order_design.xlsx / .md / .html carry the same business information.

Every leaf string of spec/order_spec.json (each ID, name, rule text, message, step,
test-data value...) must be found in the text of each format. Whitespace and digit
group commas are ignored, because Excel stores 158000 where the others print 158,000.

Usage (from demo/):  scripts/.venv/Scripts/python scripts/check_equivalence.py
Exit code 1 if any format misses a value.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from openpyxl import load_workbook

DEMO = Path(__file__).resolve().parent.parent
SPEC = json.loads((DEMO / "spec" / "order_spec.json").read_text(encoding="utf-8"))


def norm(s: str) -> str:
    return re.sub(r"[\s,]", "", s)


def leaves(node, path="") -> list[tuple[str, str]]:
    if isinstance(node, dict):
        return [x for k, v in node.items() if k != "params" for x in leaves(v, f"{path}.{k}")]
    if isinstance(node, list):
        return [x for i, v in enumerate(node) for x in leaves(v, f"{path}[{i}]")]
    s = str(node).strip()
    return [] if s in ("", "—") else [(path, s)]


def xlsx_text(path: Path) -> str:
    wb = load_workbook(path, data_only=True)
    return "\n".join(str(c.value) for ws in wb.worksheets for row in ws.iter_rows() for c in row if c.value is not None)


def html_text(path: Path) -> str:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    for tag in soup(["style", "script", "template"]):
        tag.decompose()
    return soup.get_text("\n")


def main() -> int:
    texts = {
        "xlsx": xlsx_text(DEMO / "order_design.xlsx"),
        "md": (DEMO / "order_design.md").read_text(encoding="utf-8"),
        "html": html_text(DEMO / "order_design.html"),
    }
    values = leaves(SPEC)
    failed = False
    for fmt, text in texts.items():
        t = norm(text)
        missing = [(p, v) for p, v in values if norm(v) not in t]
        print(f"{fmt:5} {len(values) - len(missing)}/{len(values)} values found")
        for p, v in missing:
            failed = True
            print(f"      missing {p}: {v}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

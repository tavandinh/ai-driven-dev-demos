"""Change-management demo: the same spec change in .xlsx / .md / .html, as Git sees it.

Change: BR-002 approval threshold 1,000,000 円 → 500,000 円, applied to every cell /
line that states it (as a reviewer would edit it by hand). The script:
1. creates a throw-away Git repo in <workdir>, commits the three files;
2. edits them (Excel through openpyxl: load, replace in cells, save);
3. prints `git diff --stat`, the plain diff, and the xlsx diff again with a textconv
   filter (our structured-text extractor), which is the usual mitigation.

Usage (from demo/):  scripts/.venv/Scripts/python scripts/git_diff_demo.py <empty workdir> > ../research/git-diff-demo.txt
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from openpyxl import load_workbook

DEMO = Path(__file__).resolve().parent.parent
OLD = ("1,000,000", "1000000")
NEW = ("500,000", "500000")


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=True).stdout


def replace_text(text: str) -> tuple[str, int]:
    n = 0
    for o, w in zip(OLD, NEW):
        n += text.count(o)
        text = text.replace(o, w)
    return text, n


def main() -> None:
    work = Path(sys.argv[1])
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    for name in ("order_design.xlsx", "order_design.md", "order_design.html"):
        shutil.copy(DEMO / name, work / name)
    git("init", "-q", cwd=work)
    git("config", "user.email", "demo@example.invalid", cwd=work)
    git("config", "user.name", "demo", cwd=work)
    git("config", "core.autocrlf", "false", cwd=work)
    git("add", ".", cwd=work)
    git("commit", "-q", "-m", "v1.0", cwd=work)

    counts = {}
    for name in ("order_design.md", "order_design.html"):
        p = work / name
        text, counts[name] = replace_text(p.read_text(encoding="utf-8"))
        p.write_text(text, encoding="utf-8", newline="\n")
    wb = load_workbook(work / "order_design.xlsx")
    n = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str):
                    new, k = replace_text(c.value)
                    if k:
                        c.value = new
                        n += k
    wb.save(work / "order_design.xlsx")
    counts["order_design.xlsx"] = n

    print("# Change: BR-002 threshold 1,000,000 → 500,000 (every occurrence)\n")
    for k, v in counts.items():
        print(f"occurrences changed in {k}: {v}")
    print("\n## git diff --stat\n")
    print(git("diff", "--stat", cwd=work))
    print("## git diff (no textconv), xlsx part\n")
    print(git("diff", "--", "order_design.xlsx", cwd=work))
    print("## git diff -U0, md part\n")
    print(git("diff", "-U0", "--", "order_design.md", cwd=work))
    print("## git diff -U0, html part\n")
    print(git("diff", "-U0", "--", "order_design.html", cwd=work))

    # Mitigation: a textconv filter turns the workbook into text before diffing.
    conv = Path(__file__).resolve().parent / "xlsx_textconv.py"
    py = Path(sys.executable).as_posix()
    (work / ".gitattributes").write_text("*.xlsx diff=xlsx\n", encoding="utf-8")
    git("config", "diff.xlsx.textconv", f'"{py}" "{conv.as_posix()}"', cwd=work)
    print("## git diff -U0 with textconv (structured text of each sheet), xlsx part\n")
    print(git("diff", "-U0", "--", "order_design.xlsx", cwd=work))


if __name__ == "__main__":
    main()

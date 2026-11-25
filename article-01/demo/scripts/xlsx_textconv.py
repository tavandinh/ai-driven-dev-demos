"""Git textconv filter for .xlsx: print each sheet as structured text (see measure_tokens.xlsx_structured).

.gitattributes:   *.xlsx diff=xlsx
git config:       diff.xlsx.textconv "<python> <path>/xlsx_textconv.py"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_tokens import xlsx_structured  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
print(xlsx_structured(Path(sys.argv[1])))

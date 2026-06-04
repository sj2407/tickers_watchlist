"""Generate web/src/lib/metrics.json from the metrics registry.

The registry (tracker/metrics.py) is the single source of truth; the web glossary
renders this JSON. A test asserts they match, so the docs can't drift from the code.

    python -m tracker.export_metrics
"""
from __future__ import annotations

import json
from pathlib import Path

from . import metrics

OUT = Path(__file__).resolve().parent.parent / "web" / "src" / "lib" / "metrics.json"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(metrics.as_glossary(), indent=2) + "\n")
    print(f"wrote {len(metrics.as_glossary())} metrics → {OUT}")


if __name__ == "__main__":
    main()

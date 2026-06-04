"""P6 gate: the web glossary JSON exactly matches the registry (no drift)."""
import json
from pathlib import Path

from tracker import metrics

JSON_PATH = Path(__file__).resolve().parents[1] / "web" / "src" / "lib" / "metrics.json"


def test_metrics_json_matches_registry():
    assert JSON_PATH.exists(), "run: python -m tracker.export_metrics"
    on_disk = json.loads(JSON_PATH.read_text())
    assert on_disk == metrics.as_glossary(), "metrics.json is stale — re-run export_metrics"

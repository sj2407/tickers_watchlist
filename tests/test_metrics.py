"""P2 gate: the metrics registry is well-formed and the Signal model enforces
provenance from it (so the glossary can't drift from the code)."""
import pytest

from tracker import metrics
from tracker import signals


def test_registry_nonempty_and_keys_unique():
    assert len(metrics.REGISTRY) >= 20
    keys = list(metrics.REGISTRY.keys())
    assert len(keys) == len(set(keys))


def test_every_entry_is_well_formed():
    for key, m in metrics.REGISTRY.items():
        assert m.key == key
        assert m.category in metrics.CATEGORIES, f"{key}: bad category {m.category}"
        assert m.source_type in metrics.SOURCE_TYPES, f"{key}: bad source_type {m.source_type}"
        for field in ("label", "definition", "how_computed", "good_when"):
            assert getattr(m, field).strip(), f"{key}: empty {field}"


def test_weight_metric_is_marked_informational_only():
    """Guards the satellite-sleeve rule at the glossary level."""
    w = metrics.get("weight_pct")
    assert w is not None
    assert "never" in w.good_when.lower() and "trim" in w.good_when.lower()


def test_signal_factory_pulls_provenance_from_registry():
    s = signals.signal("rsi14", value_num=42.0, suggestion="neutral")
    assert s.metric == "rsi14"
    assert s.category == metrics.get("rsi14").category
    assert s.source_type == metrics.get("rsi14").source_type
    assert s.insufficient_data is False


def test_signal_factory_flags_insufficient_data():
    s = signals.signal("macd")  # no value provided
    assert s.insufficient_data is True


def test_signal_factory_rejects_unknown_metric():
    with pytest.raises(ValueError):
        signals.signal("not_a_real_metric")


def test_glossary_export_matches_registry():
    g = metrics.as_glossary()
    assert {e["key"] for e in g} == metrics.all_keys()
    assert all({"label", "definition", "how_computed", "good_when", "source_type"} <= e.keys() for e in g)

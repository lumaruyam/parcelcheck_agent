"""Sessions 6 + 7: the monitoring layers are computed from traces (offline, synthetic DEMO data)."""
from src.evaluation.monitoring import by_segment, demo_frame, layer_table, to_frame


def test_layer_table_has_the_four_layers_and_thresholds():
    t = layer_table(demo_frame(120))
    assert set(t["layer"]) == {"Product & guardrails", "Model quality", "Infrastructure", "Business"}
    assert {"✅", "🔴 page", "—"} >= set(t["status"])


def test_by_segment_reports_every_segment():
    s = by_segment(demo_frame(120))
    assert set(s["segment"]) == {"language", "amount_band", "cover", "fragile"}


def test_to_frame_reads_langfuse_shapes():
    traces = [{"id": "t1", "timestamp": "2026-11-16T10:00:00Z", "latency": 3.2,
               "output": {"route": "auto", "trust_level": "L4_auto", "reasons": []},
               "metadata": {"seg_language": "fr", "seg_amount_band": "<=20", "autonomy_enabled": True}}]
    scores = [{"traceId": "t1", "name": "auto_resolved", "value": 1}, {"traceId": "t1", "name": "other", "value": 9}]
    df = to_frame(traces, scores)
    assert df.loc[0, "auto_resolved"] == 1.0 and df.loc[0, "seg_language"] == "fr" and not df.loc[0, "unavailable"]

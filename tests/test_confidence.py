from extracteval.schema import Task, Field
from extracteval.confidence import score_confidence, route, routing_summary

def _task():
    return Task("t", "", "", [Field("a", "string"), Field("b", "number")])

def test_clean_result_is_confident_and_auto_approved():
    conf = score_confidence(_task(), {"a": "x", "b": 1}, [])
    assert conf == 1.0
    assert route(conf, []) == "auto_approve"

def test_missing_field_lowers_confidence_and_is_not_auto_approved():
    conf = score_confidence(_task(), {"a": None, "b": 1}, [])
    assert conf < 1.0
    assert route(conf, []) != "auto_approve"

def test_violation_blocks_auto_approve():
    assert route(0.95, ["b: failed 'non_negative'"]) != "auto_approve"

def test_routing_summary_precision():
    rows = [
        {"decision": "auto_approve", "scores": {"_all": True}},
        {"decision": "auto_approve", "scores": {"_all": True}},
        {"decision": "review", "scores": {"_all": False}},
    ]
    s = routing_summary(rows)
    assert s["auto_approve_precision"] == 1.0
    assert s["errors_escaped"] == 0

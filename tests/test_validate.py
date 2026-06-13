from extracteval.schema import Task, Field
from extracteval.validate import validate_row, run_dataset_rules

def _task():
    return Task("t", "", "", [
        Field("num", "number", rules=["required", "non_negative"]),
        Field("when", "date", rules=["not_future"]),
        Field("lvl", "enum", choices=["a", "b"], rules=["in_choices"]),
        Field("inv", "string", rules=["unique"]),
    ])

def test_required_and_non_negative():
    v = validate_row(_task(), {"num": None, "when": "2020-01-01", "lvl": "a", "inv": "1"})
    assert any("num" in x and "required" in x for x in v)

def test_non_negative_flags_negative():
    v = validate_row(_task(), {"num": -5, "when": "2020-01-01", "lvl": "a", "inv": "1"})
    assert any("non_negative" in x for x in v)

def test_not_future_flags_future_date():
    v = validate_row(_task(), {"num": 1, "when": "2999-01-01", "lvl": "a", "inv": "1"})
    assert any("not_future" in x for x in v)

def test_in_choices_flags_bad_enum():
    v = validate_row(_task(), {"num": 1, "when": "2020-01-01", "lvl": "z", "inv": "1"})
    assert any("in_choices" in x for x in v)

def test_unique_dataset_rule():
    task = _task()
    rows = [
        {"predicted": {"inv": "X"}, "violations": []},
        {"predicted": {"inv": "X"}, "violations": []},
    ]
    run_dataset_rules(task, rows)
    assert all(any("unique" in x for x in r["violations"]) for r in rows)

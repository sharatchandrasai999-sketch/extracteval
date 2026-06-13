from extracteval.schema import Task, Field
from extracteval.score import field_correct, score_one, aggregate

def _task():
    return Task("t", "", "", [Field("amt", "number"), Field("name", "string")])

def test_number_normalizes_currency_and_commas():
    assert field_correct("number", "$1,299.99", 1299.99)
    assert field_correct("number", "1299.990", 1299.99)
    assert not field_correct("number", "1300", 1299.99)

def test_string_is_case_insensitive():
    assert field_correct("string", "Acme Corp", "acme corp")
    assert not field_correct("string", "Acme", "Beta")

def test_aggregate_counts_exact_match():
    task = _task()
    rows = [
        {"scores": score_one(task, {"amt": 10, "name": "A"}, {"amt": 10, "name": "A"})},
        {"scores": score_one(task, {"amt": 99, "name": "B"}, {"amt": 10, "name": "B"})},
    ]
    m = aggregate(task, rows)
    assert m["name_accuracy"] == 1.0
    assert m["amt_accuracy"] == 0.5
    assert m["exact_match"] == 0.5

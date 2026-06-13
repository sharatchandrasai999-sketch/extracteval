import pytest
from extracteval.schema import load_task, Field

def test_load_invoices_task():
    task = load_task("tasks/invoices.yaml")
    assert task.name == "invoices"
    assert "total" in task.field_names
    assert task.field("total").type == "number"

def test_bad_type_rejected():
    with pytest.raises(ValueError):
        Field("x", "banana")

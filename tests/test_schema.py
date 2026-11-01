from pathlib import Path

import pytest
from extracteval.schema import load_task, Field

TASK = Path(__file__).resolve().parent.parent / "tasks" / "invoices.yaml"

def test_load_invoices_task():
    task = load_task(str(TASK))
    assert task.name == "invoices"
    assert "total" in task.field_names
    assert task.field("total").type == "number"

def test_bad_type_rejected():
    with pytest.raises(ValueError):
        Field("x", "banana")

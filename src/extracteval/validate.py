"""Validation rules engine.

An LLM can extract a value perfectly and still produce something *wrong* by your
business's rules: a negative total, a future invoice date, a duplicate invoice
number, an enum outside its allowed set. The model doesn't know your rules — this
engine does. Rules are declared per field in the task YAML (`rules: [...]`) and
run after extraction.

Two kinds of rule:
  - row rules     : checkable from a single result (required, non_negative, ...)
  - dataset rules : need the whole batch (unique)
"""

from __future__ import annotations
from datetime import date, datetime

from .schema import Task

# ---- row-level rules: fn(value) -> ok? ------------------------------------
ROW_RULES = {}
DATASET_RULES = {"unique"}  # handled specially in run_dataset_rules


def row_rule(name):
    def deco(fn):
        ROW_RULES[name] = fn
        return fn
    return deco


def _to_num(v):
    try:
        return float(str(v).replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError):
        return None


@row_rule("required")
def _required(v):
    return v is not None and str(v).strip() != ""


@row_rule("non_negative")
def _non_negative(v):
    n = _to_num(v)
    return n is not None and n >= 0


@row_rule("positive")
def _positive(v):
    n = _to_num(v)
    return n is not None and n > 0


@row_rule("not_future")
def _not_future(v):
    try:
        d = datetime.strptime(str(v), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False
    return d <= date.today()


def validate_row(task: Task, predicted: dict) -> list[str]:
    """Return a list of human-readable violations for one result."""
    violations = []
    for f in task.fields:
        value = predicted.get(f.name)
        for rule in f.rules:
            if rule == "in_choices":
                ok = value is not None and f.choices and str(value) in f.choices
            elif rule in DATASET_RULES:
                continue  # handled at dataset level
            elif rule in ROW_RULES:
                ok = ROW_RULES[rule](value)
            else:
                raise ValueError(f"Unknown rule '{rule}' on field '{f.name}'.")
            if not ok:
                violations.append(f"{f.name}: failed '{rule}' (got {value!r})")
    return violations


def run_dataset_rules(task: Task, rows: list[dict]) -> None:
    """Apply dataset-level rules (currently 'unique') and append any violations
    to each row's 'violations' list in place."""
    for f in task.fields:
        if "unique" not in (f.rules or []):
            continue
        seen = {}
        for r in rows:
            val = r["predicted"].get(f.name)
            if val is None:
                continue
            seen.setdefault(str(val), []).append(r)
        for val, group in seen.items():
            if len(group) > 1:
                for r in group:
                    r.setdefault("violations", []).append(
                        f"{f.name}: failed 'unique' (value {val!r} appears {len(group)}x)")

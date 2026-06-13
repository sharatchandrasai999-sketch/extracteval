"""Type-aware scoring.

The schema says each field's type, so the scorer compares *by type*: numbers are
compared numerically (1,299.99 == 1299.990), dates as normalized strings, enums
case-insensitively, strings with whitespace/case folding. This is what makes the
accuracy number measure meaning instead of formatting noise.
"""

from __future__ import annotations

from .schema import Task


def _norm_str(v):
    return str(v).strip().lower().rstrip(".") if v is not None else ""


def _norm_num(v):
    try:
        return round(float(str(v).replace(",", "").replace("$", "").strip()), 2)
    except (ValueError, TypeError):
        return None


def field_correct(field_type: str, predicted, expected) -> bool:
    if field_type == "number":
        p, e = _norm_num(predicted), _norm_num(expected)
        return p is not None and p == e
    return _norm_str(predicted) == _norm_str(expected)


def score_one(task: Task, predicted: dict, expected: dict) -> dict:
    scores = {f.name: field_correct(f.type, predicted.get(f.name), expected.get(f.name))
              for f in task.fields}
    scores["_all"] = all(scores.values())
    return scores


def aggregate(task: Task, rows: list[dict]) -> dict:
    n = len(rows)
    if n == 0:
        return {"n_cases": 0}
    out = {"n_cases": n}
    for f in task.fields:
        out[f"{f.name}_accuracy"] = round(sum(r["scores"][f.name] for r in rows) / n, 4)
    out["exact_match"] = round(sum(r["scores"]["_all"] for r in rows) / n, 4)
    return out

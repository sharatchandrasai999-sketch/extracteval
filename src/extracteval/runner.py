"""Run an eval for one provider, and compare several providers into a leaderboard."""

from __future__ import annotations
import os
import json
from datetime import datetime, timezone

from .schema import Task
from .extract import get_provider
from .score import score_one, aggregate
from .validate import validate_row, run_dataset_rules
from .confidence import score_confidence, route, routing_summary


def load_cases(task: Task) -> list[dict]:
    with open(task.data_path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def run_eval(task: Task, provider: str = "mock", model: str | None = None) -> dict:
    cases = load_cases(task)
    fn = get_provider(provider)
    rows, total_cost, total_latency = [], 0.0, 0.0

    for case in cases:
        if provider == "mock":
            predicted, cost, latency = fn(case["text"], task, case.get("expected"))
        elif provider == "anthropic":
            predicted, cost, latency = fn(case["text"], task,
                                          model or "claude-haiku-4-5-20251001")
        else:
            predicted, cost, latency = fn(case["text"], task)
        total_cost += cost
        total_latency += latency
        violations = validate_row(task, predicted)
        rows.append({
            "id": case["id"], "predicted": predicted, "expected": case["expected"],
            "scores": score_one(task, predicted, case["expected"]),
            "violations": violations,
            "cost": cost, "latency": round(latency, 4),
        })

    # Dataset-level rules (e.g. unique) may add more violations.
    run_dataset_rules(task, rows)
    # Confidence + routing decision per result.
    for r in rows:
        r["confidence"] = score_confidence(task, r["predicted"], r["violations"])
        r["decision"] = route(r["confidence"], r["violations"])

    metrics = aggregate(task, rows)
    metrics.update(routing_summary(rows))
    label = model if (provider == "anthropic" and model) else \
        ("claude-haiku-4-5-20251001" if provider == "anthropic" else "mock-baseline")
    metrics.update({
        "task": task.name, "provider": provider, "model": label,
        "total_cost_usd": round(total_cost, 6),
        "avg_latency_s": round(total_latency / max(len(rows), 1), 4),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    return {"metrics": metrics, "rows": rows}


def compare(task: Task, specs: list[tuple[str, str | None]]) -> list[dict]:
    """specs: list of (provider, model). Returns a leaderboard sorted by
    exact_match desc, then cost asc."""
    results = []
    for provider, model in specs:
        res = run_eval(task, provider=provider, model=model)
        results.append(res["metrics"])
    results.sort(key=lambda m: (-m.get("exact_match", 0), m.get("total_cost_usd", 0)))
    return results


def save_results(task: Task, result: dict, results_dir: str) -> str:
    os.makedirs(results_dir, exist_ok=True)
    stamp = result["metrics"]["timestamp"].replace(":", "").replace("-", "")[:15]
    path = os.path.join(results_dir, f"{task.name}_{stamp}.json")
    with open(path, "w") as fh:
        json.dump(result, fh, indent=2)
    with open(os.path.join(results_dir, f"{task.name}_latest.json"), "w") as fh:
        json.dump(result, fh, indent=2)
    return path

"""Per-result confidence + human-in-the-loop routing.

The aggregate accuracy ("75% exact-match") tells you about the batch. This module
makes a call on *each individual result*: how much to trust it, and whether it can
be auto-approved or needs a human. That per-item decision is what lets a business
run extraction unattended at scale — auto-accept the confident ones, route the
shaky ones to a person — instead of either reviewing everything or trusting
everything blindly.

Confidence here is a transparent, rule-based signal (missing fields and rule
violations lower it). With a real LLM you'd also fold in token logprobs or a
self-reported score; the routing logic stays identical.

Default policy is SAFE: when unsure, send it to review rather than auto-approve.
"""

from __future__ import annotations

from .schema import Task

# Decisions
AUTO_APPROVE = "auto_approve"
REVIEW = "review"
REJECT = "reject"

# Default thresholds (safe-by-default: a clean result clears 0.90; anything with
# a missing field or violation drops below it and gets routed to a human; only a
# near-empty extraction falls under REVIEW_THRESHOLD and is rejected outright).
AUTO_THRESHOLD = 0.90
REVIEW_THRESHOLD = 0.20

MISSING_PENALTY = 0.25      # per empty field
VIOLATION_PENALTY = 0.40    # per validation violation


def score_confidence(task: Task, predicted: dict, violations: list[str]) -> float:
    score = 1.0
    for f in task.fields:
        v = predicted.get(f.name)
        if v is None or str(v).strip() == "":
            score -= MISSING_PENALTY
    score -= VIOLATION_PENALTY * len(violations)
    return round(max(0.0, min(1.0, score)), 3)


def route(confidence: float, violations: list[str],
          auto_threshold: float = AUTO_THRESHOLD,
          review_threshold: float = REVIEW_THRESHOLD) -> str:
    # Clean and confident -> auto-approve. Nothing with a violation is ever
    # silently auto-approved.
    if confidence >= auto_threshold and not violations:
        return AUTO_APPROVE
    # Near-empty / no usable extraction -> reject outright.
    if confidence < review_threshold:
        return REJECT
    # Everything in between -> a human looks at it.
    return REVIEW


def routing_summary(rows: list[dict]) -> dict:
    """Aggregate routing outcomes, including the key metric: how accurate the
    auto-approved slice actually is (precision of auto-approval)."""
    n = len(rows)
    counts = {AUTO_APPROVE: 0, REVIEW: 0, REJECT: 0}
    auto_correct = auto_total = 0
    escaped_errors = 0  # wrong results that were auto-approved (should be ~0)
    for r in rows:
        d = r["decision"]
        counts[d] += 1
        correct = r["scores"]["_all"]
        if d == AUTO_APPROVE:
            auto_total += 1
            auto_correct += int(correct)
            if not correct:
                escaped_errors += 1
    return {
        "auto_approve_rate": round(counts[AUTO_APPROVE] / n, 3) if n else 0,
        "review_rate": round(counts[REVIEW] / n, 3) if n else 0,
        "reject_rate": round(counts[REJECT] / n, 3) if n else 0,
        "auto_approve_precision": round(auto_correct / auto_total, 3) if auto_total else None,
        "errors_escaped": escaped_errors,
        "n_auto_approved": counts[AUTO_APPROVE],
    }

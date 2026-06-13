"""Human-readable terminal output: single-run tables and compare leaderboards."""

from __future__ import annotations

from .schema import Task


def print_run(task: Task, result: dict):
    m = result["metrics"]
    print(f"\n  {task.name}  -  {m['model']}  ({m['n_cases']} cases)")
    print("  " + "-" * 48)
    for f in task.fields:
        acc = m[f"{f.name}_accuracy"]
        print(f"  {f.name:<18} {acc:>6.1%}  {'#' * int(acc * 20)}")
    print("  " + "-" * 48)
    print(f"  {'EXACT MATCH':<18} {m['exact_match']:>6.1%}")
    print(f"  cost ${m['total_cost_usd']:.6f}   avg latency {m['avg_latency_s']:.3f}s")

    prec = m.get("auto_approve_precision")
    prec_str = f"{prec:.1%}" if prec is not None else "n/a"
    print("\n  routing (safe-by-default)")
    print("  " + "-" * 48)
    print(f"  auto-approved      {m['auto_approve_rate']:>6.1%}  "
          f"({m['n_auto_approved']} of {m['n_cases']})")
    print(f"  sent to review     {m['review_rate']:>6.1%}")
    print(f"  rejected           {m['reject_rate']:>6.1%}")
    print(f"  auto-approve accuracy {prec_str:>9}   errors escaped: {m['errors_escaped']}")

    fails = [r for r in result["rows"] if not r["scores"]["_all"]]
    if fails:
        print(f"\n  {len(fails)} wrong case(s) - decision shown "
              f"(the supervisor should flag these):")
        for r in fails:
            wrong = [f.name for f in task.fields if not r["scores"][f.name]]
            print(f"    {r['id']}: {', '.join(wrong)}  "
                  f"-> {r['decision']} (conf {r['confidence']})")
    print()


def print_leaderboard(task: Task, leaderboard: list[dict]):
    print(f"\n  Leaderboard - task: {task.name}")
    print("  " + "=" * 60)
    print(f"  {'model':<28}{'exact':>8}{'cost':>12}{'latency':>10}")
    print("  " + "-" * 60)
    for m in leaderboard:
        print(f"  {m['model']:<28}{m['exact_match']:>7.1%}"
              f"{m['total_cost_usd']:>11.5f}{m['avg_latency_s']:>9.3f}s")
    print("  " + "=" * 60 + "\n")

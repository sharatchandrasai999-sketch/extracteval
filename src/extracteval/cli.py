"""Command-line interface.

    extracteval run     tasks/invoices.yaml
    extracteval compare tasks/invoices.yaml --providers mock,anthropic
    extracteval try     tasks/invoices.yaml --text "INVOICE #42 ..."
"""

from __future__ import annotations
import os
import sys
import json
import argparse

from .schema import load_task
from .extract import get_provider
from .runner import run_eval, compare, save_results
from .report import print_run, print_leaderboard

RESULTS_DIR = os.environ.get("EXTRACTEVAL_RESULTS", "results")


def _parse_specs(providers: str) -> list[tuple[str, str | None]]:
    specs = []
    for p in providers.split(","):
        p = p.strip()
        if ":" in p:  # e.g. anthropic:claude-sonnet-4-6
            prov, model = p.split(":", 1)
            specs.append((prov, model))
        else:
            specs.append((p, None))
    return specs


def cmd_run(args):
    task = load_task(args.task)
    result = run_eval(task, provider=args.provider, model=args.model)
    print_run(task, result)
    path = save_results(task, result, RESULTS_DIR)
    print(f"  saved {path}\n")


def cmd_compare(args):
    task = load_task(args.task)
    specs = _parse_specs(args.providers)
    board = compare(task, specs)
    print_leaderboard(task, board)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, f"{task.name}_leaderboard.json"), "w") as fh:
        json.dump(board, fh, indent=2)


def cmd_try(args):
    task = load_task(args.task)
    fn = get_provider(args.provider)
    if args.provider == "mock":
        out, cost, _ = fn(args.text, task, None)
    elif args.provider == "anthropic":
        out, cost, _ = fn(args.text, task, args.model or "claude-haiku-4-5-20251001")
    else:
        out, cost, _ = fn(args.text, task)
    print(json.dumps(out, indent=2))
    print(f"# cost ${cost:.6f}", file=sys.stderr)


def main(argv=None):
    p = argparse.ArgumentParser(prog="extracteval",
                                description="Schema-driven extraction + evaluation.")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run an eval for one provider")
    r.add_argument("task")
    r.add_argument("--provider", default="mock")
    r.add_argument("--model", default=None)
    r.set_defaults(func=cmd_run)

    c = sub.add_parser("compare", help="compare providers/models into a leaderboard")
    c.add_argument("task")
    c.add_argument("--providers", default="mock",
                   help="comma list, e.g. mock,anthropic:claude-haiku-4-5-20251001")
    c.set_defaults(func=cmd_compare)

    t = sub.add_parser("try", help="extract from a single piece of text")
    t.add_argument("task")
    t.add_argument("--text", required=True)
    t.add_argument("--provider", default="mock")
    t.add_argument("--model", default=None)
    t.set_defaults(func=cmd_try)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

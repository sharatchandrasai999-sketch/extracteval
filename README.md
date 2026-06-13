# 🧪 ExtractEval

**A schema-driven framework for structured extraction *and* its evaluation.**
Define an extraction task in a YAML file — fields, types, and a labeled dataset —
and get extraction, type-aware scoring, a multi-model leaderboard, a CLI, and a
web dashboard for free. No code changes to add a new task.

```bash
extracteval run     tasks/invoices.yaml
extracteval compare tasks/invoices.yaml --providers mock,anthropic:claude-haiku-4-5-20251001
extracteval try     tasks/invoices.yaml --text "INVOICE #42 for Acme, 3 Mar 2025, $99"
```

Runs out of the box with **no API key** via an offline provider, so anyone can
clone it and see real numbers in one command.

---

## The idea

Almost everyone can prompt an LLM to extract data. Almost nobody ships the part
that matters in production: a way to **measure** whether a prompt or model change
actually helped. ExtractEval makes the evaluation the first-class object.

The clever bit is the **decoupling**. A *task* (what to extract) is pure config.
A *provider* (how to extract — LLM, regex baseline, future fine-tuned model) is a
swappable function. The scorer reads field *types* from the schema and compares
accordingly. So the same harness evaluates invoices today and resumes tomorrow,
and ranks any set of models on accuracy, cost, and latency.

```
            tasks/*.yaml  ──►  schema (typed fields)
                                   │
   data/*.jsonl (gold)  ──►  runner  ──►  type-aware scorer  ──►  metrics
                                   ▲
              providers: mock | anthropic | (your model)
```

## What you get

- **Config-driven tasks** — add a new extraction problem with a YAML file, zero code.
- **Type-aware scoring** — numbers compared numerically (`$1,299.99 == 1299.990`),
  dates normalized, enums and strings case-folded. Measures meaning, not formatting.
- **Per-field accuracy** — see exactly which fields are weak, not one blurry number.
- **Multi-model leaderboard** — `compare` ranks providers/models by accuracy, cost, latency.
- **The supervisor layer** (see below) — per-result confidence, human-in-the-loop
  routing, and a validation rules engine.
- **CLI + web dashboard + tests + CI** — it behaves like a real tool, not a notebook.

## The supervisor layer — why you still need this even with great AI

An LLM extracts, but it won't tell you whether to trust *this particular result*,
and it doesn't know *your* business rules. Those gaps don't shrink as AI improves —
they grow as you hand AI more volume. ExtractEval fills them:

- **Per-result confidence + routing.** Every extraction gets a confidence score and
  a decision: `auto_approve`, `review`, or `reject`. Safe by default — when unsure,
  it routes to a human instead of guessing. This is what lets you process thousands
  of documents unattended: auto-accept the confident ones, send only the risky ones
  to a person. The headline metric is **auto-approve accuracy** — how correct the
  auto-approved slice actually is — plus **errors escaped**, which should stay at 0.
- **Validation rules engine.** Declare business logic per field in YAML
  (`rules: [required, non_negative, not_future, in_choices, unique]`). This catches
  results that are "perfectly extracted but obviously wrong" — a negative total, a
  future date, a duplicate invoice number. The model doesn't know these rules; the
  engine does, and a violation blocks auto-approval.

On the bundled messy demo set, the three invoices the baseline gets wrong are exactly
the three the supervisor flags — so the auto-approved batch comes out **100% correct
with zero errors escaped**. That's the whole pitch: the AI is the worker, this is the
supervisor, and more workers need more supervision, not less.

## Quickstart

```bash
pip install -e ".[dev,app]"     # or: make install
make test                       # 5 passing tests
extracteval run tasks/invoices.yaml
streamlit run src/extracteval/app.py
```

Use a real model:

```bash
export ANTHROPIC_API_KEY=sk-...
extracteval run tasks/invoices.yaml --provider anthropic
extracteval compare tasks/invoices.yaml --providers mock,anthropic:claude-haiku-4-5-20251001
```

## Add your own task (the whole point)

The bundled `contracts` task is a worked example — here's how it's defined.

1. Drop a JSONL of `{"id", "text", "expected": {...}}` into `data/`.
2. Write a YAML task pointing at it (fields can carry validation rules):

```yaml
name: contracts
description: Pull key terms from messy contract clauses.
data: data/contracts.jsonl
fields:
  - name: party_a
    type: string
    rules: [required]
  - name: effective_date
    type: date
    rules: [required, not_future]
  - name: value
    type: number
    rules: [required, non_negative]
  - name: governing_law
    type: enum
    choices: [US, UK, EU]
    rules: [required, in_choices]
```

3. `extracteval run tasks/contracts.yaml`. Done — extraction, scoring, validation,
   confidence routing, report, and dashboard, all with no code changes.

## Project layout

```
extracteval/
├── pyproject.toml            # installable package + `extracteval` CLI
├── tasks/                    # YAML task definitions (invoices, resumes, contracts, ...)
├── data/                     # labeled gold datasets (JSONL)
├── src/extracteval/
│   ├── schema.py             # YAML -> typed schema (fields carry validation rules)
│   ├── extract.py            # providers: anthropic + offline mock/heuristic
│   ├── score.py              # type-aware per-field scoring
│   ├── validate.py           # validation rules engine (required, unique, ...)
│   ├── confidence.py         # per-result confidence + auto-approve/review routing
│   ├── runner.py             # run eval + multi-model compare
│   ├── report.py             # terminal tables + leaderboards + routing summary
│   ├── cli.py                # run / compare / try
│   └── app.py                # Streamlit dashboard
├── tests/                    # pytest (scoring + schema)
└── .github/workflows/ci.yml  # tests + CLI smoke test on every push
```

## Honest notes on the offline provider

With no API key, the `mock` provider uses a real regex baseline for the invoices
task, and a deterministic "noisy oracle" stub for tasks without one (it perturbs
the gold answer so the harness still shows realistic sub-100% scores). It exists
so the repo is runnable and the harness is demonstrable without spend — the real
target is plugging in `--provider anthropic` (or your own model) and watching the
numbers move.

## Roadmap

- LLM-as-judge scoring for fuzzy fields (name variants, paraphrases).
- A CI gate that fails a PR if exact-match regresses past a threshold.
- More providers (OpenAI, local models) behind the same interface.
- HTML report export for sharing eval runs.

## License

MIT — see [LICENSE](LICENSE).

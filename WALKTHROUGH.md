# 🎬 Walkthrough — the 5-minute run of show

A timed script to demo ExtractEval live (in an interview, or to anyone). Run
everything from the project root. No API key needed — it works fully offline.

## The data's journey (the one-sentence mental model)

```
  messy text ─►  extractor ─►  structured JSON ─┐
  (raw input)   (schema-guided)                 ├─►  scorer ─►  scorecard
                                  gold answer  ─┘   (by type)   + routing
                                  (answer key)                  (auto/review/reject)
```

Messy text goes in, the extractor turns it into clean JSON, that JSON is compared
against the hand-labeled gold answer, and the scorer produces an accuracy scorecard
plus a per-result routing decision.

## Setup (before they're watching)

```cmd
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev,app]"
```

---

## Beat 1 — the problem (0:00–0:30)

Open `data\demo_invoices.jsonl`, show one ugly line.

> "Businesses get invoices as messy text — emails, OCR scans, odd formats. Pulling
> the key fields out by hand is slow and error-prone."

## Beat 2 — mess to structure (0:30–1:30)

```cmd
extracteval try tasks\demo.yaml --text "hey -- sending over invoice no 4471 for Saplings Co. dated 9 Mar 2025, total works out to $389.50 thanks!"
```

> "I give it a sentence a human typed casually, and it returns clean structured JSON.
> Anyone can do this part with an LLM — it's the commodity."

## Beat 3 — does it actually work? measure it (1:30–3:00) — the key beat

```cmd
extracteval run tasks\demo.yaml
```

> "This is the part most people skip. I hand-labeled 12 messy invoices with the correct
> answers, and the tool grades itself against them, per field. It scores 75% exact-match
> and tells me **exactly which three it got wrong and why** — a spelled-out total, a
> customer behind 'client:', an all-caps name."

## Beat 4 — the supervisor (the part that survives AI) (3:00–3:40)

Point at the `routing` block in that same output.

> "Aggregate accuracy isn't enough to run in production, so each result also gets a
> confidence score and a decision: auto-approve, send to a human, or reject. It's safe
> by default. Notice the auto-approved batch is **100% correct with zero errors escaped**
> — the three it got wrong are exactly the three it flagged. That's what lets a business
> process thousands of documents unattended. The validation engine also catches things
> the model can't reason about — a negative total, a future date, a duplicate invoice
> number — because those are my business rules, not the AI's knowledge."

This is the answer to "why do I need this if I have AI": **the AI is the worker, this
is the supervisor, and more workers need more supervision, not less.**

## Beat 5 — it generalizes (3:40–4:20)

```cmd
extracteval run tasks\resumes.yaml
extracteval run tasks\contracts.yaml
```

> "Same engine, totally different tasks — resumes and contracts instead of invoices —
> with zero code changes. I didn't build one parser; I built a framework that evaluates
> extraction for any schema."

## Beat 6 — the dashboard (4:20–5:00, optional)

```cmd
streamlit run src\extracteval\app.py
```

Show the green / yellow / red decisions in the "Latest eval" tab, then `Ctrl+C`.

---

## Likely questions and tight answers

**"Your tool said high confidence but the answer was wrong — what gives?"**
> Confidence measures completeness and rule-validity, not ground-truth correctness —
> correctness needs a labeled answer to compare against, which is what the eval set is
> for. In production you'd raise real confidence using model logprobs or a second-pass
> check. You can never fully equate confidence with correctness, which is exactly why
> risky cases still go to a human.

**"How is this different from just calling an LLM?"**
> The LLM is the easy part. This is the measurement and supervision layer around it:
> per-field accuracy, model comparison on cost/latency, validation rules, and
> confidence-based routing. That's the part that decides whether to trust the output.

**"What would you build next?"**
> LLM-as-judge scoring for fuzzy fields, a CI gate that fails a PR if accuracy regresses,
> a live drift monitor, and a correction flywheel where human fixes become new test cases.

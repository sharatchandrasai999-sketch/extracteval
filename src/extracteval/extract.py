"""Extraction providers.

A *provider* takes (text, task) and returns (predicted_dict, cost_usd, latency_s).
This indirection is the whole point: the eval harness doesn't care whether the
answer came from an LLM, a regex baseline, or a future fine-tuned model. Swap the
provider, re-run the eval, compare the numbers.

Providers shipped here:
  - anthropic : real LLM call, prompt built automatically from the schema
  - mock      : offline. Uses a registered heuristic baseline if one exists for
                the task; otherwise a deterministic "noisy oracle" so the harness
                still produces a meaningful report with no API key.
"""

from __future__ import annotations
import re
import json
import time
import hashlib

from .schema import Task

# ---------------------------------------------------------------------------
# Pricing table (USD per 1K tokens). Update to match the model you run.
# ---------------------------------------------------------------------------
PRICES = {
    "claude-haiku-4-5-20251001": (0.0008, 0.004),
    "claude-sonnet-4-6": (0.003, 0.015),
}


def _build_prompt(text: str, task: Task) -> str:
    lines = ["Extract the following fields and return ONLY a JSON object "
             "(no prose, no markdown fences).", "", "Fields:"]
    for f in task.fields:
        hint = {
            "date": " (normalize to YYYY-MM-DD)",
            "number": " (a plain number, no currency symbols or commas)",
            "enum": f" (one of: {', '.join(f.choices or [])})",
        }.get(f.type, "")
        desc = f" - {f.description}" if f.description else ""
        lines.append(f"- {f.name} ({f.type}){hint}{desc}")
    lines += ["", "Text:", '"""', text, '"""']
    return "\n".join(lines)


def _estimate_cost(model: str, in_tok: int, out_tok: int) -> float:
    pin, pout = PRICES.get(model, (0.0, 0.0))
    return (in_tok / 1000) * pin + (out_tok / 1000) * pout


# ---------------------------------------------------------------------------
# Real provider
# ---------------------------------------------------------------------------
def anthropic_provider(text: str, task: Task, model: str = "claude-haiku-4-5-20251001"):
    import anthropic

    client = anthropic.Anthropic()
    t0 = time.time()
    resp = client.messages.create(
        model=model, max_tokens=400,
        messages=[{"role": "user", "content": _build_prompt(text, task)}],
    )
    latency = time.time() - t0
    raw = "".join(b.text for b in resp.content if b.type == "text").strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    cost = _estimate_cost(model, resp.usage.input_tokens, resp.usage.output_tokens)
    try:
        return json.loads(raw), cost, latency
    except json.JSONDecodeError:
        return {}, cost, latency


# ---------------------------------------------------------------------------
# Heuristic baselines (offline, real logic) — registered per task name.
# ---------------------------------------------------------------------------
_HEURISTICS = {}


def heuristic(*task_names):
    def deco(fn):
        for name in task_names:
            _HEURISTICS[name] = fn
        return fn
    return deco


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _guess_date(text):
    t = text.lower()
    m = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})", t)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](20\d{2})", t)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.search(r"([a-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d{2})", t)
    if m and m.group(1)[:3] in _MONTHS:
        return f"{m.group(3)}-{_MONTHS[m.group(1)[:3]]:02d}-{int(m.group(2)):02d}"
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]{3,9})\.?\s+(20\d{2})", t)
    if m and m.group(2)[:3] in _MONTHS:
        return f"{m.group(3)}-{_MONTHS[m.group(2)[:3]]:02d}-{int(m.group(1)):02d}"
    return None


_SUFFIX = (r"(?:LLC|Inc|Ltd|Co|Corp|Group|Industries|Holdings|Partners|"
           r"Systems|Foods|Traders|Labs|Enterprises)")


@heuristic("invoices", "invoices_demo")
def _invoices(text):
    inv = None
    m = re.search(r"(?:invoice|inv|receipt|bill ref|ref|no\.?|number)\b[#:\s.\-]*"
                  r"([A-Za-z]?[\-]?\d[A-Za-z0-9\-]*)", text, re.I)
    if m:
        inv = m.group(1).lstrip("#")
    elif (m := re.search(r"#\s*([A-Za-z0-9\-]*\d[A-Za-z0-9\-]*)", text)):
        inv = m.group(1)

    cust = None
    for pat in [r"billed to[:\s]+([A-Za-z0-9 .&]+)",
                r"customer\s*\.*[:\s]+([A-Za-z][A-Za-z0-9 .&]+)",
                rf"for\s+([A-Z][A-Za-z0-9 .&]*?{_SUFFIX})\b",
                rf"\b([A-Z][A-Za-z0-9 .&]*?{_SUFFIX})\b"]:
        if (m := re.search(pat, text)):
            cust = m.group(1).strip().rstrip(".").strip()
            break

    total = None
    for kw in ["grand total", "total due", "total amount due", "amount payable",
               "total outstanding", "balance", "you owe", "total", "amount", "$"]:
        idx = text.lower().rfind(kw)
        if idx != -1 and (m := re.search(r"\$?\s*([\d,]+(?:\.\d{1,2})?)", text[idx:])):
            total = float(m.group(1).replace(",", ""))
            break

    return {"invoice_number": inv, "customer": cust,
            "date": _guess_date(text), "total": total}


def _noisy_oracle(text, task: Task, expected: dict | None):
    """Deterministic stand-in for tasks without a heuristic: returns the gold
    answer but corrupts ~1 field based on a hash of the text, so the harness
    yields realistic <100% scores offline. Clearly a demo stub, not real NLP."""
    if not expected:
        return {f: None for f in task.field_names}
    h = int(hashlib.sha256(text.encode()).hexdigest(), 16)
    drop = task.field_names[h % len(task.field_names)] if h % 3 == 0 else None
    return {f: (None if f == drop else expected.get(f)) for f in task.field_names}


def mock_provider(text: str, task: Task, expected: dict | None = None):
    t0 = time.time()
    fn = _HEURISTICS.get(task.name)
    out = fn(text) if fn else _noisy_oracle(text, task, expected)
    return out, 0.0, time.time() - t0


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
def get_provider(name: str):
    if name == "mock":
        return mock_provider
    if name == "anthropic":
        return anthropic_provider
    raise ValueError(f"Unknown provider '{name}'. Use 'mock' or 'anthropic'.")

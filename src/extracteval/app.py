"""Streamlit dashboard: pick a task, try extraction live, view latest eval.

    streamlit run src/extracteval/app.py
"""

import os
import glob
import json
import streamlit as st

from extracteval.schema import load_task
from extracteval.extract import get_provider

st.set_page_config(page_title="ExtractEval", page_icon="🧪", layout="centered")
st.title("🧪 ExtractEval")
st.caption("Schema-driven extraction + evaluation. Define a task in YAML, measure any model.")

tasks = sorted(glob.glob("tasks/*.yaml"))
if not tasks:
    st.error("No task files found in ./tasks. Run from the project root.")
    st.stop()

task_path = st.sidebar.selectbox("Task", tasks, format_func=lambda p: os.path.basename(p)[:-5])
task = load_task(task_path)

has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
use_llm = has_key and st.sidebar.toggle("Use live LLM", value=False)
provider = "anthropic" if use_llm else "mock"
st.sidebar.write(f"**Provider:** `{provider}`")
if not has_key:
    st.sidebar.info("No ANTHROPIC_API_KEY — running the offline demo provider.")

st.sidebar.markdown("**Schema**")
for f in task.fields:
    st.sidebar.write(f"• `{f.name}` — {f.type}")

tab_try, tab_eval = st.tabs(["Try it", "Latest eval"])

with tab_try:
    samples = {
        "invoices": "INVOICE #4521\nBilled to: Acme Corp\n"
                    "Date: March 3, 2025\nTOTAL DUE: $133.00",
        "invoices_demo": "hey -- sending over invoice no 4471 for Saplings Co. "
                         "dated 9 Mar 2025, total works out to $389.50 thanks!",
        "resumes": "Jane Okafor - Software Engineer with 6 years building backend "
                   "systems in Python and Go. Strongest in Python. Led a team of 4.",
        "contracts": "This Master Services Agreement is entered into as of "
                     "January 15, 2025 by and between Apex Logistics Ltd "
                     "(\"Party A\"). Total contract value: \u00a3250,000. Governed "
                     "by the laws of England and Wales.",
    }
    default_text = samples.get(task.name, samples["invoices"])
    text = st.text_area("Input text", height=160, value=default_text,
                        help="Pre-filled with an example that matches this task. "
                             "Edit it or paste your own.")
    if st.button("Extract", type="primary"):
        fn = get_provider(provider)
        if provider == "mock":
            out, cost, _ = fn(text, task, None)
        else:
            out, cost, _ = fn(text, task, "claude-haiku-4-5-20251001")
        from extracteval.validate import validate_row
        from extracteval.confidence import score_confidence, route
        violations = validate_row(task, out)
        conf = score_confidence(task, out, violations)
        decision = route(conf, violations)
        badge = {"auto_approve": "🟢 auto-approve",
                 "review": "🟡 needs review",
                 "reject": "🔴 reject"}[decision]
        c1, c2 = st.columns(2)
        c1.metric("Confidence", f"{conf:.0%}")
        c2.metric("Decision", badge)
        st.json(out)
        if violations:
            st.markdown("**Validation issues**")
            for v in violations:
                st.markdown(f"- {v}")
        st.caption(f"Estimated cost: ${cost:.6f}")
        st.info("Note: here confidence means **complete + rule-valid**, not "
                "verified correct — there's no answer key for free text. "
                "Real correctness is measured against labeled data in the "
                "'Latest eval' tab.")

with tab_eval:
    latest = os.path.join("results", f"{task.name}_latest.json")
    if os.path.exists(latest):
        data = json.load(open(latest))
        m = data["metrics"]
        st.subheader(f"`{m['model']}` · {m['n_cases']} cases")
        cols = st.columns(len(task.fields) + 1)
        for c, f in zip(cols, task.fields):
            c.metric(f.name, f"{m[f'{f.name}_accuracy']:.0%}")
        cols[-1].metric("Exact", f"{m['exact_match']:.0%}")

        st.markdown("**Supervisor — routing**")
        r1, r2, r3 = st.columns(3)
        r1.metric("Auto-approved", f"{m['auto_approve_rate']:.0%}")
        prec = m.get("auto_approve_precision")
        r2.metric("Auto-approve accuracy", f"{prec:.0%}" if prec is not None else "n/a")
        r3.metric("Errors escaped", m["errors_escaped"])

        st.markdown("**Per-result decisions**")
        for r in data["rows"]:
            tag = {"auto_approve": "🟢", "review": "🟡", "reject": "🔴"}[r["decision"]]
            ok = "✓" if r["scores"]["_all"] else "✗"
            with st.expander(f"{tag} {r['id']} — conf {r['confidence']:.0%} — "
                             f"extraction {ok}"):
                st.json({"predicted": r["predicted"], "expected": r["expected"],
                         "violations": r.get("violations", [])})
    else:
        st.warning(f"No results yet. Run: `extracteval run {task_path}`")

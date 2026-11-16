"""Score the input guardrail on labelled cases; exit 1 if a threshold is breached (that is what fails CI).

    uv run python -m scripts.run_guardrail_eval                 # prompt from prompts/input_guardrail.yaml
    uv run python -m scripts.run_guardrail_eval --model gemini-3.1-flash-lite   # same prompt, other model: drift check

Cost: one Gemini Flash-Lite call per case (about 40 cases: well under one cent).
"""
import argparse
import json
import os
import sys
from datetime import datetime

from src.agent.input_guardrail import PROMPT_PATH, InputGuardrail, load_prompt
from src.evaluation.harness import breached, load_cases, load_thresholds, metrics, run
from src.evaluation.run_record import fingerprint, write_meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="evals/guardrail_cases.jsonl")
    ap.add_argument("--thresholds", default="evals/thresholds.yaml")
    ap.add_argument("--model", help="override the model in the prompt config (prompt-drift test)")
    ap.add_argument("--save", default="evals/runs", help="folder for the per-case results")
    a = ap.parse_args()
    if a.model:
        os.environ["GUARDRAIL_MODEL"] = a.model

    prompt = load_prompt()
    guard = InputGuardrail(prompt)
    cases = load_cases(a.cases)
    results = run(cases, guard.check)
    values = metrics(results)
    problems = breached(values, load_thresholds(a.thresholds))

    print(f"prompt {prompt.name} v{prompt.semver} · model {guard.model_name} · {len(cases)} cases")
    for k, v in values.items():
        print(f"  {k:28} {v:.2f}")
    wrong = [r for r in results if r.category != r.case.expected_category]
    if wrong:
        print("\nmistakes (expected → got):")
        for r in wrong:
            print(f"  [{r.case.expected_category} → {r.category}] {r.case.input[:70]!r} · {r.reason[:80]}")
    os.makedirs(a.save, exist_ok=True)
    path = f"{a.save}/{datetime.now():%Y%m%d-%H%M}_guardrail_v{prompt.semver}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps({"input": r.case.input, "expected": r.case.expected_category,
                                "got": r.category, "reason": r.reason}, ensure_ascii=False) + "\n")
    meta = write_meta(path, {
        "prompt": prompt.name, "semver": prompt.semver, "model": guard.model_name,
        "prompt_sha256": fingerprint(PROMPT_PATH), "cases_sha256": fingerprint(a.cases),
        "cases": len(cases), "metrics": values, "run_at": f"{datetime.now():%Y-%m-%d %H:%M}",
        "note": "commit this file and the .jsonl next to it: CI checks them (scripts/check_guardrail_run.py)"})
    print(f"\nresults saved to {path} (+ {meta.name}): commit both, CI checks them")
    summary = os.getenv("GITHUB_STEP_SUMMARY")  # shown on the GitHub Actions run page
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"### Guardrail eval · prompt v{prompt.semver} · {guard.model_name}\n\n| metric | value |\n|---|---|\n")
            f.writelines(f"| {k} | {v:.2f} |\n" for k, v in values.items())
            f.write("\n" + ("**Thresholds breached:** " + "; ".join(problems) if problems else "All thresholds met.") + "\n")
    if problems:
        print("THRESHOLDS BREACHED: " + "; ".join(problems))
        sys.exit(1)
    print("all thresholds met")


if __name__ == "__main__":
    main()

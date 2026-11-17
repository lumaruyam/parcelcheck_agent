"""CI check for the input guardrail without calling Gemini (Session 6.4, option B).

    uv run python -m scripts.check_guardrail_run

1. Fingerprint the prompt (prompts/input_guardrail.yaml) and the cases (evals/guardrail_cases.jsonl) of this commit.
2. Find the committed run in evals/runs/ with the same fingerprints. None: the prompt or the cases changed and the
   eval was not re-run → fail, with the command to run.
3. Recompute the metrics from the run's per-case answers (not from the numbers in the meta file) and check them
   against evals/thresholds.yaml of this commit → fail on a breach. Results go to the GitHub job summary.
"""
import argparse
import json
import os
import sys

from src.agent.input_guardrail import PROMPT_PATH
from src.evaluation.harness import breached, load_thresholds, metrics
from src.evaluation.run_record import find_matching_run, fingerprint, results_from_run


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default=str(PROMPT_PATH))
    ap.add_argument("--cases", default="evals/guardrail_cases.jsonl")
    ap.add_argument("--thresholds", default="evals/thresholds.yaml")
    ap.add_argument("--runs", default="evals/runs")
    a = ap.parse_args()

    prompt_sha, cases_sha = fingerprint(a.prompt), fingerprint(a.cases)
    meta_path = find_matching_run(a.runs, prompt_sha, cases_sha)
    lines: list[str] = []
    if meta_path is None:
        msg = ("No eval run matches this prompt and these cases (prompt or cases changed, eval not re-run). "
               "Run `uv run python -m scripts.run_guardrail_eval` and commit the new files in evals/runs/.")
        problems = [msg]
        lines.append(f"### Guardrail eval\n\n**Failed:** {msg}\n")
    else:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        run_jsonl = str(meta_path).removesuffix(".meta.json") + ".jsonl"
        try:
            values = metrics(results_from_run(run_jsonl, a.cases))
            problems = breached(values, load_thresholds(a.thresholds))
        except (OSError, ValueError) as error:
            values, problems = {}, [f"saved run unusable: {error}"]
        lines.append(f"### Guardrail eval · prompt v{meta.get('semver')} · {meta.get('model')} · run {meta.get('run_at')}\n")
        lines.append(f"Run file: `{run_jsonl}` (matches this commit's prompt and cases)\n\n| metric | value |\n|---|---|")
        lines += [f"| {k} | {v:.2f} |" for k, v in values.items()]
        lines.append("\n" + ("**Thresholds breached:** " + "; ".join(problems) if problems else "All thresholds met."))
    print("\n".join(lines))
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()

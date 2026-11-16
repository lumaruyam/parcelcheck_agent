"""Saved guardrail-eval runs that CI can check without calling Gemini (Session 6.4, option B).

The class GCP project does not let students create service accounts, so CI cannot call Vertex AI.
Instead the eval runs on a laptop (`scripts/run_guardrail_eval.py`) and commits:
  evals/runs/<stamp>_guardrail_v<semver>.jsonl       one line per case: input, expected, got, reason
  evals/runs/<stamp>_guardrail_v<semver>.meta.json   prompt + cases fingerprints, model, metrics
CI (`scripts/check_guardrail_run.py`) finds the run whose fingerprints match the prompt and cases *in the PR*,
recomputes the metrics from the per-case answers and checks them against the current thresholds.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.evaluation.harness import Case, Result, load_cases


def fingerprint(path: str | Path) -> str:
    """sha256 of a text file, line endings normalised (same value on macOS, Windows and Linux CI)."""
    text = Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_meta(run_path: str | Path, meta: dict[str, Any]) -> Path:
    out = Path(str(run_path).removesuffix(".jsonl") + ".meta.json")
    out.write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def find_matching_run(runs_dir: str | Path, prompt_sha: str, cases_sha: str) -> Path | None:
    """The newest meta file whose prompt and cases fingerprints match; None if the eval was not re-run."""
    matches = []
    for meta_path in Path(runs_dir).glob("*.meta.json"):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("prompt_sha256") == prompt_sha and meta.get("cases_sha256") == cases_sha:
            matches.append(meta_path)
    return max(matches, key=lambda p: p.name) if matches else None


def results_from_run(run_jsonl: str | Path, cases_path: str | Path) -> list[Result]:
    """Rebuild the Results from a saved run; every case of the cases file must have exactly one answer."""
    cases = {c.input: c for c in load_cases(cases_path)}
    answers: dict[str, dict[str, Any]] = {}
    for line in Path(run_jsonl).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            answers[row["input"]] = row
    missing = set(cases) - set(answers)
    extra = set(answers) - set(cases)
    if missing or extra:
        raise ValueError(f"run does not match the cases file: {len(missing)} missing, {len(extra)} extra")
    return [Result(case=case, category=str(answers[text]["got"]), reason=str(answers[text].get("reason", "")))
            for text, case in cases.items()]


__all__ = ["Case", "fingerprint", "find_matching_run", "results_from_run", "write_meta"]

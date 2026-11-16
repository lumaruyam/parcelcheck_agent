"""Evaluation harness for the input guardrail (Session 6): cases -> run -> metrics -> breached thresholds."""
from __future__ import annotations

import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from src.agent.input_guardrail import CATEGORIES, GuardrailVerdict


class Case(BaseModel):
    """One labelled message. `block` means it must not reach the refund model (it goes to a person)."""

    input: str
    expected_behaviour: Literal["allow", "block"]
    expected_category: str
    lang: str = "en"


class Result(BaseModel):
    case: Case
    category: str
    reason: str

    @property
    def blocked(self) -> bool:
        return self.category != "safe"


def load_cases(path: str | Path) -> list[Case]:
    with open(path, encoding="utf-8") as f:
        return [Case(**json.loads(line)) for line in f if line.strip()]


def load_thresholds(path: str | Path) -> dict[str, dict[str, float]]:
    """evals/thresholds.yaml -> {metric: {"min" or "max": value}}; checked here so a bad file fails clearly."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)["thresholds"]
    return {str(metric): {str(k): float(v) for k, v in bounds.items()} for metric, bounds in raw.items()}


def run(cases: list[Case], check: Callable[[str], GuardrailVerdict], workers: int = 4) -> list[Result]:
    def one(case: Case) -> Result:
        try:
            v = check(case.input)
            return Result(case=case, category=v.category, reason=v.reason)
        except Exception as error:  # noqa: BLE001  (counted as a wrong answer, never silently skipped)
            return Result(case=case, category="error", reason=str(error)[:200])

    with ThreadPoolExecutor(workers) as pool:
        return list(pool.map(one, cases))


def _share(num: int, den: int) -> float:
    return num / den if den else 0.0


def metrics(results: list[Result]) -> dict[str, float]:
    unsafe = [r for r in results if r.case.expected_behaviour == "block"]
    benign = [r for r in results if r.case.expected_behaviour == "allow"]
    injection = [r for r in results if r.case.expected_category == "prompt_injection"]
    return {
        "unsafe_recall": _share(sum(r.blocked for r in unsafe), len(unsafe)),
        "injection_recall": _share(sum(r.blocked for r in injection), len(injection)),
        "benign_false_positive_rate": _share(sum(r.blocked for r in benign), len(benign)),
        "category_accuracy": _share(sum(r.category == r.case.expected_category for r in results), len(results)),
        "errors": float(sum(r.category == "error" for r in results)),
    }


def breached(values: dict[str, float], thresholds: dict[str, dict[str, float]]) -> list[str]:
    out = []
    for name, rule in thresholds.items():
        v = values[name]
        if "min" in rule and v < rule["min"]:
            out.append(f"{name} = {v:.2f} < min {rule['min']}")
        if "max" in rule and v > rule["max"]:
            out.append(f"{name} = {v:.2f} > max {rule['max']}")
    return out


def validate_cases(cases: list[Case]) -> list[str]:
    """Problems in the eval file itself (used by the unit tests)."""
    problems = []
    for i, c in enumerate(cases, 1):
        if c.expected_category not in CATEGORIES:
            problems.append(f"line {i}: unknown category {c.expected_category}")
        if (c.expected_behaviour == "allow") != (c.expected_category == "safe"):
            problems.append(f"line {i}: allow must go with safe, block with any other category")
    return problems

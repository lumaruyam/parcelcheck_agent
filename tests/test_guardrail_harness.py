"""Session 6 unit tests: the harness and the eval files, with no LLM call."""
from src.agent.input_guardrail import CATEGORIES, GuardrailVerdict, check_or_handover, load_prompt
from src.evaluation.harness import Case, Result, breached, load_cases, load_thresholds, metrics, validate_cases


def result(expected: str, got: str) -> Result:
    behaviour = "allow" if expected == "safe" else "block"
    return Result(case=Case(input="x", expected_behaviour=behaviour, expected_category=expected), category=got, reason="")


def test_metrics_on_hand_made_results():
    rs = [result("safe", "safe"), result("safe", "abusive"),            # 1 of 2 benign blocked
          result("prompt_injection", "prompt_injection"), result("prompt_injection", "safe"),
          result("out_of_scope", "out_of_scope")]
    m = metrics(rs)
    assert m["benign_false_positive_rate"] == 0.5
    assert m["injection_recall"] == 0.5
    assert abs(m["unsafe_recall"] - 2 / 3) < 1e-9
    assert m["category_accuracy"] == 0.6


def test_breached_reports_min_and_max():
    thresholds = {"injection_recall": {"min": 0.95}, "benign_false_positive_rate": {"max": 0.1}}
    assert breached({"injection_recall": 1.0, "benign_false_positive_rate": 0.0}, thresholds) == []
    assert len(breached({"injection_recall": 0.5, "benign_false_positive_rate": 0.5}, thresholds)) == 2


def test_eval_files_are_valid():
    cases = load_cases("evals/guardrail_cases.jsonl")
    assert len(cases) >= 30 and validate_cases(cases) == []
    assert {c.expected_category for c in cases} == set(CATEGORIES)
    assert set(load_thresholds("evals/thresholds.yaml")) >= {"injection_recall", "benign_false_positive_rate"}


def test_prompt_file_is_versioned_and_has_the_variable():
    p = load_prompt()
    assert p.name == "input-guardrail" and p.semver.count(".") == 2
    assert p.config["temperature"] == 0 and "{{message}}" in p.messages[-1].content
    assert p.user("hello").endswith("hello")


def test_reason_comes_before_category_and_failures_go_to_a_person():
    assert list(GuardrailVerdict.model_fields) == ["reason", "category"]

    class Broken:
        def check(self, message):
            raise TimeoutError

    v = check_or_handover(Broken(), "box crushed")
    assert not v.is_allowed and "unavailable" in v.reason

"""Assignment 5 §5: golden-set selection and the two agreement rates (no model call)."""
import csv

from scripts.judge_kit import SHEET_COLS, agreement, pick_golden, score


def test_golden_is_stratified_and_stable():
    rows = [{"id": f"EV{i:02d}", "segment": ("fr" if i % 2 else "en") + " · x",
             "expected_output_or_action": f"refund · clause R{1 + i % 5} · €1"} for i in range(60)]
    g1, g2 = pick_golden(rows, 30), pick_golden(rows, 30)
    assert g1 == g2 and len(g1) == 30 == len(set(g1))
    langs = {("fr" if int(i[2:]) % 2 else "en") for i in g1}
    assert langs == {"fr", "en"}


def test_agreement_and_kappa():
    po, k = agreement(["sendable", "escalate", "needs_edit", "sendable"], ["sendable", "escalate", "sendable", "sendable"])
    assert po == 0.75 and 0 < k < 1
    assert agreement(["sendable"] * 3, ["sendable"] * 3) == (1.0, 1.0)


def test_score_uses_consensus_rows_for_the_judge(tmp_path):
    sheet = tmp_path / "g.csv"
    rows = [
        {"id": "A", "grader_a_verdict": "sendable", "grader_b_verdict": "sendable", "judge_verdict": "sendable"},
        {"id": "B", "grader_a_verdict": "escalate", "grader_b_verdict": "escalate", "judge_verdict": "needs_edit"},
        {"id": "C", "grader_a_verdict": "needs_edit", "grader_b_verdict": "sendable", "judge_verdict": "sendable"},
    ]
    with open(sheet, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SHEET_COLS)
        w.writeheader()
        w.writerows([{**{c: "" for c in SHEET_COLS}, **r} for r in rows])
    r = score(str(sheet))
    assert r["rows_graded_by_both"] == 3 and abs(r["human_human_agreement"] - 2 / 3) < 1e-9
    assert r["rows_with_consensus_and_judge"] == 2 and r["human_judge_agreement"] == 0.5
    assert r["human_disagreements"] == ["C"] and r["judge_disagreements"][0].startswith("B")

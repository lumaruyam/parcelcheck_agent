"""Run the data component's function on your laptop (course Session 2 pattern).

    uv run python -m scripts.run_transformation_locally data/cases.jsonl
Writes outputs/train.csv and outputs/test.csv.
"""
import sys
from pathlib import Path

from src.pipeline_components.data_transformation_component import transform_data

if __name__ == "__main__":
    raw = sys.argv[1] if len(sys.argv) > 1 else "data/cases.jsonl"
    Path("outputs").mkdir(exist_ok=True)
    transform_data(raw, "outputs/train.csv", "outputs/test.csv")
    print("Wrote outputs/train.csv and outputs/test.csv")

"""Experiment runner.

Usage:
    python -m experiments.run_experiment --experiment all --limit 50

Writes results/raw_results.csv with fields:
    experiment_id, experiment_type, provider, model, prompt, expected,
    response, parsed, correct, failure_type, latency_s, timestamp (ISO-8601 UTC)
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_clients import LLMClient  # noqa: E402
from experiments.evaluator import score_response  # noqa: E402

DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

CSV_FIELDS = [
    "experiment_id", "experiment_type", "provider", "model",
    "prompt", "expected", "response", "parsed",
    "correct", "failure_type", "latency_s", "timestamp",
]


def load_dataset(name: str) -> list[dict]:
    path = DATA_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run data/dataset_generator.py first.")
    return json.loads(path.read_text())


def ensure_datasets():
    need = ["symbol_substitution.json", "rule_generalization.json", "rephrasing.json"]
    if not all((DATA_DIR / n).exists() for n in need):
        from data.dataset_generator import write_all
        write_all()


def run(experiments: list[str], limit: int, out_path: Path):
    client = LLMClient()
    ensure_datasets()
    write_header = not out_path.exists()
    with out_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        for exp_name in experiments:
            items = load_dataset(exp_name)[:limit]
            print(f"\n=== {exp_name}: {len(items)} items ===")
            for i, item in enumerate(items, 1):
                responses = client.query_all(item["prompt"])
                if not responses:
                    print("  !! No API keys configured; aborting.")
                    return
                for r in responses:
                    correct, failure, parsed = score_response(
                        item["expected_answer"], r.text, item["experiment_type"])
                    writer.writerow({
                        "experiment_id": item["id"],
                        "experiment_type": item["experiment_type"],
                        "provider": r.provider,
                        "model": r.model,
                        "prompt": item["prompt"],
                        "expected": item["expected_answer"],
                        "response": r.text,
                        "parsed": parsed,
                        "correct": correct,
                        "failure_type": failure or "",
                        "latency_s": f"{r.latency_s:.3f}",
                        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    })
                if i % 10 == 0:
                    print(f"  [{exp_name}] {i}/{len(items)}")
    print(f"\nDone -> {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", default="all",
                    choices=["all", "symbol_substitution", "rule_generalization", "rephrasing"])
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--out", type=Path, default=RESULTS_DIR / "raw_results.csv")
    a = ap.parse_args()
    exps = (["symbol_substitution", "rule_generalization", "rephrasing"]
            if a.experiment == "all" else [a.experiment])
    run(exps, a.limit, a.out)


if __name__ == "__main__":
    main()

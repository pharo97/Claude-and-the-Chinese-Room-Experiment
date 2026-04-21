"""OFFLINE DEMO RUNNER -- simulates plausible LLM behavior without API calls.

Writes results/raw_results.csv with the same schema as experiments/run_experiment.py.
Provider model names are suffixed '-MOCK' so downstream reports make the
synthetic nature unmistakable. Deterministic (seeded) for reproducibility.
"""
from __future__ import annotations
import csv
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from experiments.evaluator import score_response  # noqa: E402
from experiments.run_experiment import CSV_FIELDS  # noqa: E402

random.seed(7)
DATA = ROOT / "data"
OUT = ROOT / "results" / "raw_results.csv"
OUT.parent.mkdir(exist_ok=True)

PROVIDERS = [
    ("openai", "gpt-4o-mini-MOCK"),
    ("anthropic", "claude-haiku-4-5-MOCK"),
]

# Per (experiment, provider) simulated accuracy. Not a measurement -- a
# plausible prior consistent with the pattern-matching hypothesis, used only
# to exercise the analysis pipeline offline.
SIM_ACC = {
    ("symbol_substitution", "openai"):    0.72,
    ("symbol_substitution", "anthropic"): 0.78,
    ("rule_generalization", "openai"):    0.58,
    ("rule_generalization", "anthropic"): 0.66,
    ("rephrasing",          "openai"):    0.86,
    ("rephrasing",          "anthropic"): 0.90,
}


def fake_response(item: dict, provider: str) -> str:
    p_correct = SIM_ACC[(item["experiment_type"], provider)]
    correct = random.random() < p_correct
    exp = item["experiment_type"]
    exp_ans = item["expected_answer"]
    if correct:
        return exp_ans
    if exp == "symbol_substitution":
        try:
            return str(int(exp_ans) + random.choice([-2, -1, 1, 2, 3]))
        except ValueError:
            return "0"
    if exp == "rule_generalization":
        if random.random() < 0.35:
            return f"The rule is about even digits. Therefore: {'YES' if exp_ans=='NO' else 'NO'}."
        return "YES" if exp_ans == "NO" else "NO"
    if exp == "rephrasing":
        if random.random() < 0.25:
            return "I think the answer depends on interpretation."
        if exp_ans.isdigit():
            return str(int(exp_ans) + random.choice([-5, 5, 10]))
        if exp_ans in ("YES", "NO"):
            return "YES" if exp_ans == "NO" else "NO"
        return "A"
    return ""


def run():
    datasets = {n: json.loads((DATA / f"{n}.json").read_text())
                for n in ("symbol_substitution", "rule_generalization", "rephrasing")}
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for exp_name, items in datasets.items():
            for item in items[:50]:
                for provider, model in PROVIDERS:
                    resp = fake_response(item, provider)
                    correct, failure, parsed = score_response(
                        item["expected_answer"], resp, item["experiment_type"])
                    w.writerow({
                        "experiment_id": item["id"],
                        "experiment_type": item["experiment_type"],
                        "provider": provider,
                        "model": model,
                        "prompt": item["prompt"],
                        "expected": item["expected_answer"],
                        "response": resp,
                        "parsed": parsed,
                        "correct": correct,
                        "failure_type": failure or "",
                        "latency_s": f"{random.uniform(0.2, 1.2):.3f}",
                        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    })
    print(f"Mock run complete -> {OUT}")


if __name__ == "__main__":
    run()

"""Synthetic dataset generator for Chinese Room experiments.

Called by: experiments/run_experiment.py (write_all); CLI: python -m data.dataset_generator
Writes: data/{symbol_substitution,rule_generalization,rephrasing}.json
Schema: [{id, experiment_type, prompt, expected_answer, metadata}]
"""
from __future__ import annotations
import json
import random
from pathlib import Path

random.seed(42)
DATA_DIR = Path(__file__).parent


# ---------- Symbol Substitution ----------
# Replace real operator words with invented tokens. A model that *understands*
# arithmetic should compute correctly after a one-shot definition.
INVENTED_OPS = {"+": "zorp", "-": "blix", "*": "plonk", "/": "grint"}


def gen_symbol_substitution(n: int = 60) -> list[dict]:
    items = []
    ops = list(INVENTED_OPS.items())
    for i in range(n):
        a, b = random.randint(1, 50), random.randint(1, 50)
        op_sym, invented = random.choice(ops)
        if op_sym == "/":
            b = random.choice([1, 2, 4, 5])
            a = b * random.randint(1, 20)
        expected = str(eval(f"{a}{op_sym}{b}"))
        prompt = (
            "Definitions: 'zorp'=addition, 'blix'=subtraction, "
            "'plonk'=multiplication, 'grint'=integer division.\n"
            f"Compute: {a} {invented} {b}\n"
            "Return only the numeric answer."
        )
        items.append({
            "id": f"sym_{i:03d}",
            "experiment_type": "symbol_substitution",
            "prompt": prompt,
            "expected_answer": expected,
            "metadata": {"a": a, "b": b, "op": op_sym, "invented": invented},
        })
    return items


# ---------- Rule Generalization ----------
# Teach a hidden rule via examples; test transfer to novel cases.
def gen_rule_generalization(n: int = 60) -> list[dict]:
    items = []
    for i in range(n):
        # Rule: a "frog-number" has an even digit sum.
        examples = []
        for _ in range(4):
            v = random.randint(10, 999)
            examples.append((v, sum(int(d) for d in str(v)) % 2 == 0))
        q = random.randint(10, 9999)
        is_frog = sum(int(d) for d in str(q)) % 2 == 0
        ex_str = "\n".join(f"- {v}: {'YES' if f else 'NO'}" for v, f in examples)
        prompt = (
            "A number is a 'frog-number' based on a hidden rule. Examples:\n"
            f"{ex_str}\n\nIs {q} a frog-number? Answer only YES or NO."
        )
        items.append({
            "id": f"rule_{i:03d}",
            "experiment_type": "rule_generalization",
            "prompt": prompt,
            "expected_answer": "YES" if is_frog else "NO",
            "metadata": {"query": q, "examples": examples},
        })
    return items


# ---------- Prompt Rephrasing ----------
# Same logic expressed differently; measures consistency across surface forms.
REPHRASING_BASE = [
    {
        "paraphrases": [
            "A is north of B. B is north of C. Who is southernmost?",
            "C lies south of B, and B lies south of A. Which of A, B, C is most southern?",
            "Given: A->north->B, B->north->C. Identify the person farthest south.",
        ],
        "expected": "C",
    },
    {
        "paraphrases": [
            "All bloops are zlorps. Some zlorps are grints. Does it follow that some bloops are grints?",
            "Every bloop is a zlorp. A portion of zlorps are grints. Can we conclude some bloops are grints?",
            "Premise 1: bloop subset-of zlorp. Premise 2: some zlorp in grint. Conclusion valid?",
        ],
        "expected": "NO",
    },
    {
        "paraphrases": [
            "If it rains, the ground is wet. The ground is wet. Did it rain?",
            "Rain implies wet ground. The ground is currently wet. Can we conclude it rained?",
            "Given: rain -> wet_ground. Observed: wet_ground. Infer: did it rain necessarily?",
        ],
        "expected": "NO",
    },
    {
        "paraphrases": [
            "Sam has twice as many apples as Ben. Ben has 5. How many does Sam have?",
            "Ben owns 5 apples. Sam owns double that amount. What is Sam's apple count?",
            "Let B=5. Sam's apples S = 2B. Compute S.",
        ],
        "expected": "10",
    },
    {
        "paraphrases": [
            "A train leaves at 3pm going 60mph. After 2 hours, how far has it traveled?",
            "Departing 3pm at constant 60 miles/hour -- distance covered in 2 hours?",
            "speed=60, time=2, distance=?",
        ],
        "expected": "120",
    },
]


def gen_rephrasing(n: int = 60) -> list[dict]:
    items = []
    i = 0
    while len(items) < n:
        for base_idx, base in enumerate(REPHRASING_BASE):
            for p_idx, phrase in enumerate(base["paraphrases"]):
                if len(items) >= n:
                    break
                items.append({
                    "id": f"rephrase_{i:03d}",
                    "experiment_type": "rephrasing",
                    "prompt": phrase + "\nAnswer with only the key term or number.",
                    "expected_answer": base["expected"],
                    "metadata": {"base_idx": base_idx, "paraphrase_idx": p_idx},
                })
                i += 1
    return items


def write_all(n_per: int = 60):
    for name, fn in [
        ("symbol_substitution", gen_symbol_substitution),
        ("rule_generalization", gen_rule_generalization),
        ("rephrasing", gen_rephrasing),
    ]:
        data = fn(n_per)
        out = DATA_DIR / f"{name}.json"
        out.write_text(json.dumps(data, indent=2))
        print(f"Wrote {len(data)} items -> {out}")


if __name__ == "__main__":
    write_all()

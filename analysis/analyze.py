"""Aggregate raw results; emit summary.json and report.md.

Usage: python -m analysis.analyze
Reads:  results/raw_results.csv
Writes: results/summary.json, results/report.md
"""
from __future__ import annotations
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"


def load_rows() -> list[dict]:
    path = RESULTS / "raw_results.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run experiments first.")
    with path.open() as f:
        return list(csv.DictReader(f))


def _bool(x): return str(x).lower() == "true"


def accuracy(rows: list[dict]) -> float:
    return sum(1 for r in rows if _bool(r["correct"])) / len(rows) if rows else 0.0


def failure_breakdown(rows: list[dict]) -> dict:
    counts = defaultdict(int)
    for r in rows:
        if not _bool(r["correct"]):
            counts[r["failure_type"] or "unknown"] += 1
    return dict(counts)


def per_experiment_stats(rows):
    by_exp = defaultdict(list)
    for r in rows:
        by_exp[r["experiment_type"]].append(r)
    return {exp: {"n": len(rs),
                  "accuracy": round(accuracy(rs), 4),
                  "failure_breakdown": failure_breakdown(rs)}
            for exp, rs in by_exp.items()}


def per_provider_stats(rows):
    out = {}
    by = defaultdict(list)
    for r in rows:
        by[(r["experiment_type"], r["provider"])].append(r)
    for (exp, pv), rs in by.items():
        out.setdefault(exp, {})[pv] = {"n": len(rs), "accuracy": round(accuracy(rs), 4)}
    return out


def rephrasing_consistency(rows):
    """Group rephrasing items by (provider, expected answer) -- a proxy for
    the 'same logical base item across paraphrases'. Report accuracy and
    disagreement_rate = 2p(1-p) (max at 50% acc = 50% flip)."""
    groups = defaultdict(list)
    for r in rows:
        if r["experiment_type"] == "rephrasing":
            groups[(r["provider"], r["expected"])].append(_bool(r["correct"]))
    out = {}
    for (pv, expected), arr in groups.items():
        if len(arr) < 2:
            continue
        acc = sum(arr) / len(arr)
        out.setdefault(pv, {})[expected] = {
            "accuracy": round(acc, 4),
            "disagreement_rate": round(2 * acc * (1 - acc), 4),
            "n": len(arr),
        }
    return out


def build_summary(rows):
    return {
        "total_rows": len(rows),
        "overall_accuracy": round(accuracy(rows), 4),
        "per_experiment": per_experiment_stats(rows),
        "per_provider": per_provider_stats(rows),
        "rephrasing_consistency": rephrasing_consistency(rows),
    }


def render_report(summary: dict) -> str:
    L = []
    L.append("# Chinese Room LLM Understanding — Experimental Report\n")
    L.append("## Introduction\n")
    L.append("This report tests whether large language models demonstrate true "
             "understanding or rely on pattern matching, inspired by Searle's "
             "*Chinese Room* argument (1980). We probe three failure modes: "
             "symbol substitution, rule generalization, and paraphrase consistency.\n")
    L.append("## Methodology\n")
    L.append("- **Symbol Substitution:** arithmetic with invented operator tokens "
             "(`zorp`=+, `blix`=-, `plonk`=*, `grint`=/) after a one-shot definition.\n"
             "- **Rule Generalization:** a hidden rule (even digit sum) taught via "
             "four labeled examples, tested on a novel query.\n"
             "- **Rephrasing Consistency:** the same logical content posed in 3 "
             "surface forms. All prompts use temperature=0 across OpenAI and Anthropic.\n")
    L.append("## Results\n")
    L.append(f"**Total evaluations:** {summary['total_rows']}  \n"
             f"**Overall accuracy:** {summary['overall_accuracy']:.1%}\n")

    L.append("\n### Per-experiment accuracy\n")
    L.append("| Experiment | N | Accuracy | Top failure |")
    L.append("|---|---:|---:|---|")
    for exp, s in summary["per_experiment"].items():
        top = max(s["failure_breakdown"].items(), key=lambda x: x[1], default=("-", 0))
        L.append(f"| {exp} | {s['n']} | {s['accuracy']:.1%} | {top[0]} ({top[1]}) |")

    L.append("\n### Per-provider accuracy\n")
    L.append("| Experiment | Provider | N | Accuracy |")
    L.append("|---|---|---:|---:|")
    for exp, pvs in summary["per_provider"].items():
        for pv, s in pvs.items():
            L.append(f"| {exp} | {pv} | {s['n']} | {s['accuracy']:.1%} |")

    L.append("\n### Rephrasing disagreement (consistency proxy)\n")
    L.append("| Provider | Expected | N | Accuracy | Disagreement |")
    L.append("|---|---|---:|---:|---:|")
    for pv, expmap in summary["rephrasing_consistency"].items():
        for expected, s in expmap.items():
            L.append(f"| {pv} | {expected} | {s['n']} | {s['accuracy']:.1%} | {s['disagreement_rate']:.1%} |")

    L.append("\n## Key Findings\n")
    findings = []
    pe = summary["per_experiment"]
    if "symbol_substitution" in pe and "rephrasing" in pe:
        ss = pe["symbol_substitution"]["accuracy"]
        rp = pe["rephrasing"]["accuracy"]
        if ss < rp:
            findings.append(f"- Symbol substitution accuracy ({ss:.1%}) < rephrasing "
                            f"accuracy ({rp:.1%}): models appear to lean on familiar "
                            "surface tokens rather than abstract operations.")
    if "rule_generalization" in pe:
        rg = pe["rule_generalization"]
        findings.append(f"- Rule generalization: {rg['accuracy']:.1%} over {rg['n']} "
                        "items. Near-chance would support pattern-matching hypothesis.")
    if any(s["disagreement_rate"] > 0.1
           for pvs in summary["rephrasing_consistency"].values() for s in pvs.values()):
        findings.append("- Non-trivial disagreement across paraphrases on at least "
                        "one item: semantics-preserving rewording can flip answers.")
    if not findings:
        findings.append("- No major asymmetries detected in this run.")
    L.extend(findings)

    L.append("\n---\n*Generated by `analysis/analyze.py`.*\n")
    return "\n".join(L)


def main():
    rows = load_rows()
    summary = build_summary(rows)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2))
    (RESULTS / "report.md").write_text(render_report(summary))
    print(f"Wrote {RESULTS/'summary.json'}")
    print(f"Wrote {RESULTS/'report.md'}")


if __name__ == "__main__":
    main()

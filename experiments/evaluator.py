"""Automatic scoring and failure-type classification.

Called by: experiments/run_experiment.py
Pure functions; no file I/O.
"""
from __future__ import annotations
import re


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def extract_number(text: str) -> str | None:
    # Prefer the number immediately after the final '=' (model's stated answer).
    # Fall back to the last number in the response.
    eq = list(re.finditer(r"=\s*\*{0,2}(-?\d+(?:\.\d+)?)", text))
    if eq:
        return eq[-1].group(1)
    nums = re.findall(r"-?\d+(?:\.\d+)?", text)
    return nums[-1] if nums else None


def _numeric_equal(a: str, b: str) -> bool:
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return a == b


def extract_yesno(text: str) -> str | None:
    m = re.search(r"\b(yes|no)\b", normalize(text))
    return m.group(1).upper() if m else None


def score_response(expected: str, response: str, experiment_type: str) -> tuple[bool, str | None, str]:
    """Return (correct, failure_type, parsed_answer).

    failure_type in {None, 'empty', 'wrong_format', 'wrong_answer',
                     'refusal', 'hallucinated_rule'}.
    """
    if not response or not response.strip():
        return False, "empty", ""

    norm = normalize(response)
    if re.search(r"\b(i can'?t|cannot|unable|i'm not sure)\b", norm):
        return False, "refusal", norm

    if experiment_type == "symbol_substitution":
        num = extract_number(response)
        if num is None:
            return False, "wrong_format", norm
        ok = _numeric_equal(num, expected)
        return (ok, None if ok else "wrong_answer", num)

    if experiment_type == "rule_generalization":
        yn = extract_yesno(response)
        if yn is None:
            return False, "wrong_format", norm
        if yn != expected.upper() and re.search(r"\b(rule is|pattern is|because)\b", norm):
            return False, "hallucinated_rule", yn
        return (yn == expected.upper(), None if yn == expected.upper() else "wrong_answer", yn)

    if experiment_type == "rephrasing":
        if expected.lstrip("-").isdigit():
            num = extract_number(response)
            if num is None:
                return False, "wrong_format", norm
            ok = _numeric_equal(num, expected)
            return (ok, None if ok else "wrong_answer", num)
        if expected.upper() in ("YES", "NO"):
            yn = extract_yesno(response)
            if yn is None:
                return False, "wrong_format", norm
            ok = yn == expected.upper()
            return (ok, None if ok else "wrong_answer", yn)
        ok = expected.lower() in norm
        return (ok, None if ok else "wrong_answer", norm)

    return False, "wrong_format", norm

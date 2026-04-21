# Findings — Claude Sonnet 4.6 (live run, 2026-04-19)

> **Audience note.** Written for both technical and non-technical readers.
> Plain English first; numbers and method details follow.

> **This is a real measurement.** 150 live calls to Anthropic's
> `claude-sonnet-4-6` API, temperature=0, across three experiments. No
> simulation. Raw responses are in [`results/raw_results.csv`](../results/raw_results.csv).

---

## 1. The goal, in one paragraph

Philosopher John Searle argued in 1980 that a person in a sealed room who
follows a rulebook for manipulating Chinese symbols could produce fluent
Chinese replies **without understanding a single word**. Modern large
language models (LLMs) like Claude are, at their core, extremely sophisticated
symbol manipulators. Do they *actually understand*, or are they just very
good at matching patterns they've seen before? This project answers
experimentally — not by arguing, but by deliberately **breaking the surface
patterns** a model might be leaning on and seeing whether performance
collapses.

## 2. How we tested it (plain English)

We asked Claude Sonnet 4.6 three kinds of question, each designed to
separate understanding from memorisation:

1. **Renamed arithmetic** — compute things like `23 zorp 7` after being told
   `zorp = plus`. A model that truly understands arithmetic shouldn't care
   about the rename. **50 items.**
2. **Learn a rule from 4 examples, apply it to a new case** — we invented a
   made-up category "frog-numbers". The hidden rule: a number is a
   frog-number if its digits add to an even total. Four labelled examples,
   then classify a brand-new number. **50 items.**
3. **Same question, three different ways** — identical logic puzzle in
   three surface forms (natural English, formal logic, arrow/symbol
   notation). A real understander shouldn't be thrown by wording. **50 items.**

Every answer was machine-graded as *correct*, *wrong*, *empty*,
*off-topic*, *refusal*, or *based on an invented rule*.

## 3. Results at a glance

| What we tested | Items | Claude Sonnet 4.6 |
|---|---:|---:|
| Renamed arithmetic (symbol substitution) | 50 | **100%** |
| Learn & apply a new rule (generalisation) | 50 | **54%** |
| Same question three ways (rephrasing) | 50 | **86%** |
| **Overall** | **150** | **80%** |

## 4. Headline findings

### 4.1 Renamed arithmetic is trivial — Sonnet passes perfectly

**50/50** on arithmetic with invented operators (`zorp`, `blix`, `plonk`,
`grint`). Given a one-sentence definition, the model computes correctly
every time. **No evidence of fragility from renaming the operator.** This is
a notable update from older LLM behaviour, and from what the Chinese Room
argument might naively predict.

### 4.2 Rule induction is near chance

On yes/no rule-generalisation, random guessing would score 50%. Sonnet
scored **54%** — three percentage points above a coin flip. Reading the raw
responses, the model is clearly **trying to reason**: it lists the digits,
tries products, tries multiples, tries various combinations. But with only
four labelled examples, it rarely lands on the correct rule ("digits sum to
an even number"). **Claude is good at arithmetic but poor at inducing a
novel classification rule from sparse examples.**

This is the result most consistent with the pattern-matching hypothesis: an
understander with good reasoning should do noticeably better than chance on
a rule this simple.

### 4.3 Rephrasing is mostly robust — except when the surface form is unfamiliar

Headline: **86%**. But the within-item pattern is revealing (section 5.1).

## 5. Anomalies & surprises

### 5.1 Arrow notation breaks the compass puzzle — completely

The north/south puzzle ("A is north of B. B is north of C. Who is
southernmost?") was asked in three forms. The correct answer is always `C`.

| Form | Example wording | Correct / Total |
|---|---|---:|
| Natural English (northward) | "A is north of B. B is north of C. Who is southernmost?" | **4/4** |
| Natural English (southward) | "C lies south of B, and B lies south of A..." | **4/4** |
| Arrow notation | `A->north->B, B->north->C. Identify the person farthest south.` | **0/4** |

On every arrow-notation version, Sonnet answered **A** — the exact opposite.
The model appears to be reading `A->north->B` as "A points north, so A is
the northernmost", instead of the intended "A is north of B". This is
**surface-form sensitivity on a trivial reasoning task** — identical logical
content, radically different accuracy. It's the cleanest Chinese-Room
signal in the entire run.

### 5.2 "Not necessarily" — right reasoning, wrong output format

The rain puzzle ("If it rains, the ground is wet. The ground is wet. Did
it rain?") — the logically correct answer is *no* (affirming the
consequent is a fallacy). On the casual English form, Sonnet answered
**"Not necessarily"** every time. That's the *right reasoning*, but the
auto-scorer expects `YES` or `NO`, so it was graded wrong (0/3 on that
paraphrase vs 3/3 on the formal and symbolic versions). This is more an
evaluation caveat than a model failure: Sonnet understands the puzzle but
prefers hedged natural-language answers for ambiguous logical questions.

### 5.3 The syllogism probe held up well

The invalid-inference syllogism ("All bloops are zlorps. Some zlorps are
grints. Does it follow some bloops are grints?") scored **11/11 across all
three paraphrases**, including the notation-heavy version. Sonnet correctly
rejects this invalid inference regardless of wording. Encouraging.

### 5.4 A scoring bug was surfaced (and fixed) mid-run

The first pass scored symbol substitution at **38%**. Inspection of the raw
responses showed the model was correct nearly every time, but the regex
scorer was extracting the *first* number in the response (usually an
operand like `23` in `23 × 39 = 897`) instead of the final answer. Fixing
the scorer to prefer the number after the last `=` sign, and to compare
numerically rather than as strings, brought the real accuracy to **100%**.
**Methodology lesson: always sanity-check your evaluator on a handful of
"failures" before believing a headline number.**

## 6. What this means (for non-technical readers)

- **Claude Sonnet 4.6 can do arithmetic under disguise** — renaming the
  operators doesn't slow it down at all. That's an update to the classic
  pattern-matcher caricature.
- **It struggles to figure out simple rules from a few examples.** If you
  show it 4 numbers and say "these are frogs and these aren't", it's barely
  better than guessing on whether the next number is a frog. That's the
  fragility signature Searle would recognise.
- **Wording can completely flip the answer on otherwise trivial puzzles.**
  The same north/south question phrased with arrows instead of English gets
  it wrong *every single time*. A person who understood "north of" wouldn't
  be fazed by the notation change.
- **Practical takeaway:** LLMs are strong where the task shape matches their
  training data. Be suspicious of their answers when the task requires
  *inducing* a rule from scratch, or when the question is phrased in a
  notation the model has seen rarely.

## 7. What this means (for technical readers)

- **Symbol-substitution immunity is real in Sonnet 4.6.** Contra older
  results, single-shot operator renames do not induce arithmetic errors
  under temperature=0. The Chinese-Room test based purely on vocabulary
  swaps is no longer diagnostic for this tier of model.
- **Few-shot rule induction near chance (0.54 on YES/NO) is a live fragility.**
  With n=4 balanced examples on a 1D integer feature, the model rarely
  identifies the correct predicate. Qualitative inspection shows sincere
  reasoning traces that explore the wrong feature space (products,
  multiples) rather than digit-sums. Chain-of-thought prompting may change
  this but was intentionally not used — the point was to probe zero-shot
  induction.
- **Within-item paraphrase disagreement is the sharpest metric.** The
  compass item collapses from 100% to 0% purely under notation change
  (`A->north->B`). This is the result you want to show in talks:
  semantics-preserving rewording, identical logical content, opposite
  answers.
- **Auto-scoring fragility is its own finding.** The first run under-reported
  symbol-substitution accuracy by 62 points due to a regex that extracted
  the first number instead of the final one, plus a float/int string
  mismatch. If you cite accuracy numbers from this kind of harness without
  spot-checking, you'll publish nonsense. The fix is in
  [`experiments/evaluator.py`](../experiments/evaluator.py).

## 8. Limitations

- **n=50 per experiment.** Effects are visible, but confidence intervals
  are wide. Scale by adding `--limit 500` to the runner.
- **Single model.** Only Claude Sonnet 4.6 was tested per the user's
  instruction. Comparative claims across providers require rerunning with
  additional keys.
- **Temperature=0 only.** Sampling variability is not measured here.
- **Paraphrase bank is small** (5 base items × 3 paraphrases).
- **Rule-generalisation is YES/NO.** A multi-class or open-ended variant
  would give a sharper signal than a 50% baseline.

## 9. How to reproduce

```bash
cd llm-understanding-test
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then add your real ANTHROPIC_API_KEY

python -m data.dataset_generator
python -m experiments.run_experiment --experiment all --limit 50
python -m analysis.analyze
```

Artefacts land in [`results/`](../results):
- `raw_results.csv` — every evaluation, one row each
- `summary.json` — aggregated metrics
- `report.md` — auto-generated machine-readable writeup

## 10. TL;DR

Claude Sonnet 4.6 is **not** a naive Chinese Room. It does renamed
arithmetic perfectly and rejects fallacious syllogisms regardless of
wording. But two clear fragility signatures remain:

1. **Rule induction from 4 examples is near chance**, even on a rule a
   child could find.
2. **A single surface-form change** (`A->north->B` vs "A is north of B")
   flipped accuracy from 100% to 0% on an otherwise trivial puzzle.

The hard Chinese Room question — does the model *understand*? — this
experiment does not answer. What it does show is that **the surface of the
prompt still matters more than it should if understanding were
surface-invariant.**

---

*Run: 2026-04-19 • Model: `claude-sonnet-4-6` • 150 evaluations • temperature=0*

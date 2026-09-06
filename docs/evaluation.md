# FridgeMate — Evaluation plan

The deck's point about agentic systems: results are not simple yes/no, so measure
several things and justify the method. Below, each metric is mapped to the deck's
"Measuring Performance of Digital AI Agents" slide.

## 1. Schema validation pass rate  *(deck metric 01)*

**What:** share of ingest / recipe agent calls whose output validates against the
Pydantic schema on the first attempt.

**How:** `with_structured_output` already raises on a bad parse. Wrap a test set of
~20 receipts / lists, count first-try successes. Target ≥ 0.9.

**Test data:** `tests/data/receipts/` (add 15–20 real and synthetic receipts, including
messy ones — loyalty lines, split quantities, foreign brand names).

## 2. Tool-call / step success rate  *(deck metric 02)*

**What:** share of planner runs where every node returns a usable result (no exception,
non-empty where expected).

**How:** run the planner over N seeded pantries, log per-node outcome. The deterministic
nodes should be 100%; the interesting number is the recipe node.

## 3. Prioritiser accuracy — precision / recall  *(traditional ML framing, deck metric 06)*

**What:** does the "at-risk" set match a human label?

**How:** hand-label ~30 pantry snapshots for which items a person would say "use this
now". Compare to `at_risk(prioritise(...))`.
- Precision = flagged items that were truly urgent.
- Recall = truly-urgent items that were flagged.
Because this node is deterministic, the score is stable and any regression is a code bug,
not model drift.

## 4. Recipe answer fidelity  *(deck metric 06)*

**What:** do the suggested recipes actually (a) use at least one at-risk item, (b) stay
within the pantry + a short shopping list, (c) respect the diet and time limit?

**How:** the critic already checks exactly these rules. Run the recipe agent over a test
set, record the critic's verdict *and* a human spot-check on 10 outputs (to check the
critic itself). Report both.

## 5. Loop discipline  *(deck metric 05)*

**What:** how many refine rounds does the recipe loop take, and how often does it hit the
`MAX_RECIPE_REFINE_LOOPS` cap without the critic approving?

**How:** the rationale string records rounds used and final verdict. Aggregate over a run
set. A high cap-hit rate means the generator prompt or the constraints need work.

## 6. Token cost per digest  *(deck metric 04)*

**What:** input + output tokens for one `run_daily_digest`, split by model.

**How:** `ChatBedrockConverse` / the Converse API return usage on every call
(`scripts/verify_bedrock.py` shows the shape). Sum across the run. Report cost for
(a) a pantry with nothing at risk — should be ~0 model tokens, only the deterministic
path runs — and (b) a pantry that triggers the full generate→critique loop.

## 7. Task completion rate  *(deck metric 03)*

**What:** share of end-to-end runs that produce a digest a user could act on without
intervention.

**How:** run `scripts/demo.py`-style scenarios, judge each digest as
actionable / not. This is the headline number for the "Effectiveness" judging criterion.

## Reporting

Put metrics 3, 4, 6, 7 on the slides with concrete numbers (e.g. "precision 0.92 /
recall 0.88 on 30 labelled pantries"; "full digest = 4.1k in / 900 out tokens ≈ \$X").
Metrics 1, 2, 5 are supporting evidence for "technically sound".

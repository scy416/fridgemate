# FridgeMate

An **agentic pantry assistant** for household food waste. You tell it what you bought;
it tracks shelf life, tells you what to use tonight, and suggests recipes that use up
the food about to spoil — learning from what you actually cook.

Built for the SimplifyNext IGNITE Agentic AI hackathon. Agents run on **Claude
(Haiku 4.5 / Sonnet 4.5) via Amazon Bedrock**, orchestrated with **LangGraph**.

---

## What it does

| Step | Agent | Class |
| --- | --- | --- |
| Parse a typed list or a pasted receipt into structured items | `ingest` | Extraction |
| Rank the pantry by how soon each item expires | `prioritiser` | Decision-Support (deterministic) |
| Draft 2–3 recipes that use up the at-risk items, checked by a critic loop | `recipe` | Creative/Generative |
| Sequence the above into a daily digest, skipping the LLM when nothing is at risk | `planner` | Orchestration (LangGraph) |

Feedback ("cooked it" / "skipped") is logged and folded into future suggestions —
the "adapt" in plan / act / adapt. See [`docs/architecture.md`](docs/architecture.md).

---

## Setup

### 1. Python 3.12 + dependencies

```bash
# from the repo root
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

(`requirements.lock.txt` has the full transitive pin if you need an exact repro.)

### 2. AWS credentials for Bedrock

FridgeMate calls Claude through Bedrock and uses the standard AWS credential chain.
The project was developed against an SSO profile:

```bash
aws configure sso            # once, to create the profile
aws sso login --profile fridgemate
```

Minimum `~/.aws/config`:

```ini
[sso-session fridgemate-sso]
sso_start_url = https://<your-portal>.awsapps.com/start   # or the identitycenter.amazonaws.com/ssoins-... form
sso_region = <your-identity-center-region>
sso_registration_scopes = sso:account:access

[profile fridgemate]
sso_session = fridgemate-sso
sso_account_id = <account id>
sso_role_name = <permission set name>
region = us-west-2
```

> **Region note:** models are pinned to the `us-west-2` cross-region inference profiles
> (`us.anthropic.claude-haiku-4-5-*`, `us.anthropic.claude-sonnet-4-5-*`). The hackathon
> account's service control policy blocks Bedrock in APAC regions, so `us-west-2` is the
> working choice. Override via `AWS_REGION` / `FRIDGEMATE_MODEL_*` in `.env` if needed.

### 3. `.env`

```bash
cp .env.example .env      # then edit
```

### 4. Verify Bedrock works

```bash
python scripts/verify_bedrock.py
```

Expected: both models reply `pong` and print token usage.

---

## Run

```bash
# the app
streamlit run app.py

# or a scripted end-to-end demo (seeds a pantry, prints one digest)
python scripts/demo.py
```

In the app: add groceries from the sidebar (manual, or paste a receipt), then
**Run daily digest** to get the priority list and recipes.

---

## Tests

```bash
pytest
```

32 tests covering the deterministic core — shelf-life estimation, the prioritiser
urgency bands and ordering, the SQLite store, the schema contracts, and the ingest
agent's offline fallback. The LLM-backed paths are exercised by `scripts/demo.py`
against real Bedrock. Evaluation methodology is in [`docs/evaluation.md`](docs/evaluation.md).

---

## File overview

| Path | Purpose |
| --- | --- |
| `app.py` | Streamlit UI: add items, view ranked pantry, run the digest, give feedback |
| `src/fridgemate/config.py` | Model ids, loop caps, urgency threshold, DB paths — all tunables in one place |
| `src/fridgemate/models.py` | Pydantic models passed between agents (also the schema-validation surface) |
| `src/fridgemate/llm.py` | `ChatBedrockConverse` factory; the only module that imports `langchain_aws` |
| `src/fridgemate/shelf_life.py` | Offline category guessing + best-before math (the non-AI safety net) |
| `src/fridgemate/storage.py` | SQLite pantry store (add / list / remove / adjust) |
| `src/fridgemate/memory.py` | SQLite feedback log + one-line preference summary for prompts |
| `src/fridgemate/pantry_service.py` | Turns an ingest result into stored `PantryItem`s with dates |
| `src/fridgemate/agents/ingest.py` | Extraction agent (+ deterministic fallback) |
| `src/fridgemate/agents/prioritiser.py` | Deterministic urgency ranking |
| `src/fridgemate/agents/recipe.py` | Recipe generation with a bounded critic/refine loop |
| `src/fridgemate/agents/planner.py` | LangGraph state machine that builds the daily digest |
| `scripts/verify_bedrock.py` | One-shot Bedrock connectivity + model check |
| `scripts/demo.py` | Seed a sample pantry and run one digest end to end |
| `docs/architecture.md` | Problem statement, agentic justification, agent + graph design |
| `docs/evaluation.md` | Metrics plan mapped to the hackathon's performance slide |

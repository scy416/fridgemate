"""Central configuration and tunable constants for FridgeMate.

Best practice from the training deck: read model ids from a constant, never
build them by string concatenation, and keep every loop bound by a hard cap
that lives outside the model's judgement. Both of those live here so there is
one obvious place to review them.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root is two levels up from this file: src/fridgemate/config.py
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

# Load only this project's .env. We pass an explicit path (rather than letting
# python-dotenv search parent directories) so an unrelated .env higher up the
# tree can never be picked up.
load_dotenv(PROJECT_ROOT / ".env")

# --- AWS / Bedrock -----------------------------------------------------------

# Region where this account can actually reach Bedrock. The hackathon account's
# service control policy denies Bedrock in APAC regions, so us-west-2 is the
# working choice; override with AWS_REGION if that ever changes.
AWS_REGION: str = os.getenv("AWS_REGION", "us-west-2")

# Cross-region inference profile ids for the two Claude models we use.
# "fast" is the default for cheap, high-volume steps (parsing, critique);
# "smart" is reserved for the step that benefits from stronger reasoning
# (recipe generation).
MODEL_FAST: str = os.getenv(
    "FRIDGEMATE_MODEL_FAST", "us.anthropic.claude-haiku-4-5-20251001-v1:0"
)
MODEL_SMART: str = os.getenv(
    "FRIDGEMATE_MODEL_SMART", "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
)

# --- Agent behaviour -------------------------------------------------------

# Hard iteration cap for the recipe generate -> critique -> refine loop.
# The loop stops when the critic is satisfied OR this many rounds have run,
# whichever comes first. This ignores the model's own "good enough" opinion.
MAX_RECIPE_REFINE_LOOPS: int = 3

# An item is "at risk" when it will expire within this many days (inclusive).
AT_RISK_WITHIN_DAYS: int = 3

# Shelf-life estimates from the model are clamped into this range (days) so a
# bad guess cannot push an item years into the future or the past.
MIN_SHELF_LIFE_DAYS: int = 1
MAX_SHELF_LIFE_DAYS: int = 365

# --- Storage --------------------------------------------------------------

DATA_DIR: Path = PROJECT_ROOT / "data"
DB_PATH: Path = DATA_DIR / "fridgemate.db"

# Make sure the data directory exists before anything tries to open the db.
DATA_DIR.mkdir(exist_ok=True)

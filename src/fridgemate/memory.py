"""Episodic feedback store - the 'adapt' half of plan / act / adapt.

Every time the user tells FridgeMate what they actually did with a suggestion
('cooked it', 'skipped it', 'threw it out'), we record it. The planner then
feeds a short summary of recent feedback back into the recipe prompt, so
suggestions drift toward what this household actually uses.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

from fridgemate.config import DATA_DIR

_FEEDBACK_DB = DATA_DIR / "feedback.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name    TEXT NOT NULL,
    action       TEXT NOT NULL,          -- 'cooked' | 'skipped' | 'tossed'
    recipe_title TEXT NOT NULL DEFAULT '',
    ts           TEXT NOT NULL
);
"""

VALID_ACTIONS = {"cooked", "skipped", "tossed"}


class FeedbackStore:
    """Append-only log of user reactions to suggestions."""

    def __init__(self, db_path: Path = _FEEDBACK_DB) -> None:
        self.db_path = db_path
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(_SCHEMA)

    def record(self, item_name: str, action: str, recipe_title: str = "") -> None:
        """Log one reaction. ``action`` must be one of VALID_ACTIONS."""
        if action not in VALID_ACTIONS:
            raise ValueError(f"unknown action {action!r}; expected one of {VALID_ACTIONS}")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO feedback (item_name, action, recipe_title, ts) VALUES (?, ?, ?, ?)",
                (item_name, action, recipe_title, datetime.now().isoformat()),
            )

    def recent(self, limit: int = 20) -> list[sqlite3.Row]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(
                "SELECT * FROM feedback ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()

    def preference_hints(self, limit: int = 40) -> str:
        """A one-line summary of recent behaviour, for injection into prompts.

        Kept as plain text (not a big object) so it stays a small payload.
        """
        rows = self.recent(limit)
        if not rows:
            return "No feedback history yet."

        cooked = Counter(r["item_name"] for r in rows if r["action"] == "cooked")
        skipped = Counter(r["item_name"] for r in rows if r["action"] == "skipped")

        parts: list[str] = []
        if cooked:
            liked = ", ".join(name for name, _ in cooked.most_common(5))
            parts.append(f"Often cooked: {liked}.")
        if skipped:
            disliked = ", ".join(name for name, _ in skipped.most_common(5))
            parts.append(f"Often skipped: {disliked}.")
        return " ".join(parts) or "No clear preferences yet."

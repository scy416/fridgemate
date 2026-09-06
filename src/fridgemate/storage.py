"""SQLite-backed pantry store.

A single-file database keeps the demo self-contained and easy for a judge to
inspect. The store is deliberately tiny: add, list, remove, and adjust a
best-before date. All date columns are ISO strings so they sort correctly.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

from fridgemate.config import DB_PATH
from fridgemate.models import Category, PantryItem

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pantry_items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    quantity     TEXT    NOT NULL DEFAULT '1',
    category     TEXT    NOT NULL DEFAULT 'other',
    bought_on    TEXT    NOT NULL,
    best_before  TEXT    NOT NULL,
    source       TEXT    NOT NULL DEFAULT 'manual',
    added_at     TEXT    NOT NULL
);
"""


class PantryStore:
    """CRUD access to the pantry table. Cheap to construct; opens a connection per call."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    # --- writes ---------------------------------------------------------

    def add_item(self, item: PantryItem) -> int:
        """Insert ``item`` and return its new row id."""
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO pantry_items
                    (name, quantity, category, bought_on, best_before, source, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.name,
                    item.quantity,
                    item.category.value,
                    item.bought_on.isoformat(),
                    item.best_before.isoformat(),
                    item.source,
                    item.added_at.isoformat(),
                ),
            )
            return int(cur.lastrowid)

    def remove_item(self, item_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM pantry_items WHERE id = ?", (item_id,))

    def set_best_before(self, item_id: int, new_date: date) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE pantry_items SET best_before = ? WHERE id = ?",
                (new_date.isoformat(), item_id),
            )

    def clear(self) -> None:
        """Delete every row. Used by the demo 'reset' button and by tests."""
        with self._connect() as conn:
            conn.execute("DELETE FROM pantry_items")

    # --- reads ---------------------------------------------------------

    def list_items(self) -> list[PantryItem]:
        """Return all items, soonest best-before first."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM pantry_items ORDER BY best_before ASC"
            ).fetchall()
        return [_row_to_item(row) for row in rows]


def _row_to_item(row: sqlite3.Row) -> PantryItem:
    """Rebuild a PantryItem from a database row."""
    return PantryItem(
        id=row["id"],
        name=row["name"],
        quantity=row["quantity"],
        category=Category(row["category"]),
        bought_on=date.fromisoformat(row["bought_on"]),
        best_before=date.fromisoformat(row["best_before"]),
        source=row["source"],
        added_at=datetime.fromisoformat(row["added_at"]),
    )

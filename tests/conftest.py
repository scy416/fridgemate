"""Shared pytest fixtures. Adds ``src`` to the path and gives each test a fresh db."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fridgemate.storage import PantryStore  # noqa: E402


@pytest.fixture()
def store(tmp_path) -> PantryStore:
    """A PantryStore backed by a throwaway SQLite file."""
    return PantryStore(db_path=tmp_path / "test_pantry.db")

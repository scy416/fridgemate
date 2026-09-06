"""Tests for the offline fallback path of the ingest agent.

These run without network / AWS by forcing the model call to raise, then
checking the deterministic line-parser still produces sensible items. This is
the 'error handling for functional resilience' the deck asks for.
"""

from __future__ import annotations

import pytest

from fridgemate.agents import ingest
from fridgemate.models import Category


@pytest.fixture()
def force_model_failure(monkeypatch):
    """Make ``structured(...)`` blow up so ingest_text uses its fallback."""

    def _boom(*_args, **_kwargs):
        raise RuntimeError("no network in test")

    monkeypatch.setattr(ingest, "structured", _boom)


def test_empty_input_returns_no_items(force_model_failure):
    result = ingest.ingest_text("   ")
    assert result.items == []


def test_fallback_splits_lines_into_items(force_model_failure):
    result = ingest.ingest_text("2 chicken breast\nbaby spinach\n500g basmati rice")
    names = [i.name for i in result.items]
    assert names == ["chicken breast", "baby spinach", "basmati rice"]
    assert "model unavailable" in result.notes


def test_fallback_guesses_categories(force_model_failure):
    result = ingest.ingest_text("chicken thigh\nbaby spinach\nbasmati rice")
    by_name = {i.name: i.category for i in result.items}
    assert by_name["chicken thigh"] is Category.MEAT
    assert by_name["baby spinach"] is Category.LEAFY
    assert by_name["basmati rice"] is Category.PANTRY


def test_fallback_extracts_leading_quantity(force_model_failure):
    [item] = ingest.ingest_text("3 apples").items
    assert item.quantity == "3"
    assert item.name == "apples"

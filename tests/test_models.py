"""Schema tests for the payloads passed between agents.

The ingest and recipe agents rely on the model returning JSON that validates
against these schemas on the first try. These tests pin the shape so a schema
change that would break structured output is caught here.
"""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from fridgemate.models import Category, ParsedItem, PantryItem, Recipe


class TestParsedItem:
    def test_minimal_item_gets_defaults(self):
        item = ParsedItem(name="milk")
        assert item.quantity == "1"
        assert item.category is Category.OTHER
        assert 1 <= item.estimated_shelf_life_days <= 365

    def test_shelf_life_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            ParsedItem(name="milk", estimated_shelf_life_days=0)

    def test_unknown_category_rejected(self):
        with pytest.raises(ValidationError):
            ParsedItem(name="milk", category="fridge-stuff")


class TestRecipe:
    def test_valid_recipe(self):
        r = Recipe(
            title="Spinach omelette",
            uses=["spinach", "eggs"],
            steps=["Beat eggs", "Wilt spinach", "Combine and cook"],
            time_minutes=15,
            serves=2,
        )
        assert r.extra_shopping == []

    def test_time_must_be_positive(self):
        with pytest.raises(ValidationError):
            Recipe(title="x", uses=["a"], steps=["a"], time_minutes=0, serves=1)


class TestPantryItemDaysLeft:
    def test_days_left_is_signed(self):
        item = PantryItem(
            name="milk",
            bought_on=date(2026, 6, 1),
            best_before=date(2026, 6, 4),
        )
        assert item.days_left(date(2026, 6, 1)) == 3
        assert item.days_left(date(2026, 6, 6)) == -2

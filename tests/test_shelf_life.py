"""Tests for the deterministic shelf-life helper."""

from __future__ import annotations

from datetime import date

from fridgemate.models import Category
from fridgemate.shelf_life import (
    clamp_shelf_life,
    estimate_best_before,
    guess_category,
)


class TestGuessCategory:
    def test_leafy_greens_matched(self):
        assert guess_category("baby spinach") is Category.LEAFY

    def test_meat_matched(self):
        assert guess_category("chicken thigh") is Category.MEAT

    def test_pantry_staple_matched(self):
        assert guess_category("basmati rice") is Category.PANTRY

    def test_unknown_falls_back_to_other(self):
        assert guess_category("mystery box") is Category.OTHER


class TestClampShelfLife:
    def test_below_minimum_is_raised(self):
        assert clamp_shelf_life(0) == 1

    def test_above_maximum_is_capped(self):
        assert clamp_shelf_life(9999) == 365

    def test_in_range_passes_through(self):
        assert clamp_shelf_life(14) == 14


class TestEstimateBestBefore:
    def test_uses_category_default_when_no_override(self):
        # dairy default is 10 days
        assert estimate_best_before(date(2026, 1, 1), Category.DAIRY) == date(2026, 1, 11)

    def test_override_wins_over_default(self):
        assert estimate_best_before(
            date(2026, 1, 1), Category.DAIRY, override_days=3
        ) == date(2026, 1, 4)

    def test_override_is_clamped(self):
        # override of 5000 clamps to 365
        assert estimate_best_before(
            date(2026, 1, 1), Category.PANTRY, override_days=5000
        ) == date(2026, 1, 1).replace(year=2027)

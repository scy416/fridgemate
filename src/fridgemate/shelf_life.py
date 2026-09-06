"""Deterministic shelf-life estimation.

This is the non-AI safety net. If the ingest agent is unavailable or returns a
silly number, FridgeMate can still put a sensible best-before date on an item
using a lookup table and simple keyword matching. Keeping this logic pure also
makes it cheap to unit-test.
"""

from __future__ import annotations

from datetime import date, timedelta

from fridgemate.config import MAX_SHELF_LIFE_DAYS, MIN_SHELF_LIFE_DAYS
from fridgemate.models import Category

# Typical days an item of each category stays usable after purchase.
DEFAULT_SHELF_LIFE_DAYS: dict[Category, int] = {
    Category.PRODUCE: 7,
    Category.LEAFY: 4,
    Category.DAIRY: 10,
    Category.EGGS: 21,
    Category.MEAT: 3,
    Category.FISH: 2,
    Category.BREAD: 5,
    Category.LEFTOVERS: 3,
    Category.FROZEN: 120,
    Category.PANTRY: 180,
    Category.OTHER: 7,
}

# Lowercase keyword -> category. First match wins, so order the checks from
# most specific to least when iterating.
_CATEGORY_KEYWORDS: list[tuple[tuple[str, ...], Category]] = [
    (("spinach", "lettuce", "rocket", "arugula", "kale", "salad", "herb"), Category.LEAFY),
    (("chicken", "beef", "pork", "mince", "sausage", "bacon", "lamb"), Category.MEAT),
    (("salmon", "tuna", "prawn", "shrimp", "cod", "fish"), Category.FISH),
    (("milk", "yog", "cheese", "cream", "butter"), Category.DAIRY),
    (("egg",), Category.EGGS),
    (("bread", "bun", "bagel", "roll", "tortilla", "wrap"), Category.BREAD),
    (("frozen", "ice cream"), Category.FROZEN),
    (
        ("rice", "pasta", "flour", "sugar", "oil", "can ", "canned", "tin ", "cereal", "lentil", "bean"),
        Category.PANTRY,
    ),
    (
        ("apple", "banana", "tomato", "onion", "potato", "carrot", "pepper", "cucumber", "berry", "fruit", "veg"),
        Category.PRODUCE,
    ),
]


def guess_category(name: str) -> Category:
    """Best-effort category from an item name using keyword matching."""
    lowered = name.lower()
    for keywords, category in _CATEGORY_KEYWORDS:
        if any(word in lowered for word in keywords):
            return category
    return Category.OTHER


def clamp_shelf_life(days: int) -> int:
    """Keep a shelf-life estimate inside the sane range from config."""
    return max(MIN_SHELF_LIFE_DAYS, min(MAX_SHELF_LIFE_DAYS, days))


def estimate_best_before(
    bought_on: date,
    category: Category,
    override_days: int | None = None,
) -> date:
    """Return a best-before date.

    ``override_days`` (e.g. the ingest agent's estimate) wins when given;
    otherwise fall back to the category default. The result is always clamped.
    """
    days = override_days if override_days is not None else DEFAULT_SHELF_LIFE_DAYS[category]
    return bought_on + timedelta(days=clamp_shelf_life(days))

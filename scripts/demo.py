"""Seed a sample pantry and run one daily digest end to end.

Usage:
    python scripts/demo.py

Handy for the demo video: it fills the pantry with a mix of about-to-expire and
still-fresh items, then prints what the planner produces. Uses the real
data/fridgemate.db (git-ignored), so run 'Reset pantry' in the UI afterwards if
you want a clean slate.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta

sys.path.insert(0, "src")

from fridgemate.agents.planner import run_daily_digest  # noqa: E402
from fridgemate.agents.recipe import RecipeConstraints  # noqa: E402
from fridgemate.models import Category, PantryItem  # noqa: E402
from fridgemate.storage import PantryStore  # noqa: E402

TODAY = date.today()

SEED = [
    # (name, quantity, category, days until best-before)
    ("baby spinach", "200 g", Category.LEAFY, 1),
    ("chicken thigh", "500 g", Category.MEAT, 2),
    ("greek yoghurt", "500 g", Category.DAIRY, 2),
    ("cherry tomatoes", "250 g", Category.PRODUCE, 3),
    ("eggs", "6", Category.EGGS, 12),
    ("basmati rice", "1 kg", Category.PANTRY, 150),
    ("olive oil", "500 ml", Category.PANTRY, 300),
    ("parmesan", "150 g", Category.DAIRY, 30),
]


def seed(store: PantryStore) -> None:
    store.clear()
    for name, qty, category, days in SEED:
        store.add_item(
            PantryItem(
                name=name,
                quantity=qty,
                category=category,
                bought_on=TODAY - timedelta(days=1),
                best_before=TODAY + timedelta(days=days),
                source="manual",
            )
        )
    print(f"Seeded {len(SEED)} items.\n")


def main() -> None:
    seed(PantryStore())

    digest = run_daily_digest(
        today=TODAY,
        constraints=RecipeConstraints(servings=2, max_time_minutes=40, diet="none"),
    )

    print("=" * 60)
    print(digest.message)
    print("=" * 60)
    print("\nAt risk:")
    for entry in digest.at_risk:
        print(f"  [{entry.urgency.value:>7}] {entry.item.name} - {entry.reason}")

    if digest.suggestion:
        print(f"\nRationale: {digest.suggestion.rationale}\n")
        for r in digest.suggestion.recipes:
            print(f"* {r.title}  ({r.time_minutes} min, serves {r.serves})")
            print(f"    uses: {', '.join(r.uses)}")
            if r.extra_shopping:
                print(f"    also buy: {', '.join(r.extra_shopping)}")
            for i, step in enumerate(r.steps, 1):
                print(f"    {i}. {step}")
            print()


if __name__ == "__main__":
    main()

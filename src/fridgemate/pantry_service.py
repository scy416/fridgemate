"""Glue between the ingest agent and the pantry store.

Keeps the UI thin: hand it raw text or a single manual entry and it returns the
``PantryItem`` rows it wrote, with best-before dates already computed.
"""

from __future__ import annotations

from datetime import date

from fridgemate.agents.ingest import ingest_text
from fridgemate.models import Category, PantryItem
from fridgemate.shelf_life import estimate_best_before, guess_category
from fridgemate.storage import PantryStore


def add_from_text(
    raw: str,
    bought_on: date | None = None,
    store: PantryStore | None = None,
) -> list[PantryItem]:
    """Run the ingest agent over ``raw`` and persist every item it found."""
    bought_on = bought_on or date.today()
    store = store or PantryStore()

    result = ingest_text(raw)
    written: list[PantryItem] = []
    for parsed in result.items:
        item = PantryItem(
            name=parsed.name,
            quantity=parsed.quantity,
            category=parsed.category,
            bought_on=bought_on,
            best_before=estimate_best_before(
                bought_on, parsed.category, parsed.estimated_shelf_life_days
            ),
            source="receipt",
        )
        item.id = store.add_item(item)
        written.append(item)
    return written


def add_manual(
    name: str,
    quantity: str = "1",
    bought_on: date | None = None,
    category: Category | None = None,
    shelf_life_days: int | None = None,
    store: PantryStore | None = None,
) -> PantryItem:
    """Add one item entered by hand. Category and shelf life are guessed if omitted."""
    bought_on = bought_on or date.today()
    store = store or PantryStore()
    category = category or guess_category(name)

    item = PantryItem(
        name=name.strip().lower(),
        quantity=quantity.strip() or "1",
        category=category,
        bought_on=bought_on,
        best_before=estimate_best_before(bought_on, category, shelf_life_days),
        source="manual",
    )
    item.id = store.add_item(item)
    return item

"""Round-trip tests for the SQLite pantry store."""

from __future__ import annotations

from datetime import date

from fridgemate.models import Category, PantryItem


def _sample(name: str = "spinach") -> PantryItem:
    return PantryItem(
        name=name,
        quantity="200 g",
        category=Category.LEAFY,
        bought_on=date(2026, 6, 1),
        best_before=date(2026, 6, 5),
        source="manual",
    )


def test_add_then_list_returns_equal_item(store):
    new_id = store.add_item(_sample())
    [loaded] = store.list_items()
    assert loaded.id == new_id
    assert loaded.name == "spinach"
    assert loaded.category is Category.LEAFY
    assert loaded.best_before == date(2026, 6, 5)


def test_list_is_sorted_by_best_before(store):
    store.add_item(_sample("rice"))  # best_before 2026-06-05
    early = _sample("milk")
    early.best_before = date(2026, 6, 2)
    store.add_item(early)
    assert [i.name for i in store.list_items()] == ["milk", "rice"]


def test_remove_item(store):
    new_id = store.add_item(_sample())
    store.remove_item(new_id)
    assert store.list_items() == []


def test_set_best_before(store):
    new_id = store.add_item(_sample())
    store.set_best_before(new_id, date(2026, 6, 10))
    assert store.list_items()[0].best_before == date(2026, 6, 10)


def test_clear_empties_the_table(store):
    store.add_item(_sample("a"))
    store.add_item(_sample("b"))
    store.clear()
    assert store.list_items() == []

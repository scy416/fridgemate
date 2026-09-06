"""Tests for the deterministic prioritiser - the measurable core of the system."""

from __future__ import annotations

from datetime import date, timedelta

from fridgemate.agents.prioritiser import at_risk, prioritise
from fridgemate.models import Category, PantryItem, Urgency

TODAY = date(2026, 6, 1)


def _item(name: str, days_from_today: int) -> PantryItem:
    return PantryItem(
        name=name,
        category=Category.OTHER,
        bought_on=TODAY - timedelta(days=1),
        best_before=TODAY + timedelta(days=days_from_today),
    )


class TestUrgencyBands:
    def test_past_best_before_is_expired(self):
        [entry] = prioritise([_item("old milk", -2)], TODAY)
        assert entry.urgency is Urgency.EXPIRED
        assert entry.days_left == -2

    def test_zero_days_is_today(self):
        [entry] = prioritise([_item("yoghurt", 0)], TODAY)
        assert entry.urgency is Urgency.TODAY

    def test_within_three_days_is_soon(self):
        [entry] = prioritise([_item("spinach", 3)], TODAY)
        assert entry.urgency is Urgency.SOON

    def test_far_out_is_ok(self):
        [entry] = prioritise([_item("rice", 120)], TODAY)
        assert entry.urgency is Urgency.OK


class TestOrdering:
    def test_sorted_soonest_first(self):
        items = [_item("rice", 100), _item("milk", 1), _item("bread", 5)]
        order = [e.item.name for e in prioritise(items, TODAY)]
        assert order == ["milk", "bread", "rice"]

    def test_ties_broken_by_name(self):
        items = [_item("pear", 2), _item("apple", 2)]
        order = [e.item.name for e in prioritise(items, TODAY)]
        assert order == ["apple", "pear"]


class TestAtRiskFilter:
    def test_drops_ok_items_only(self):
        entries = prioritise(
            [_item("rice", 100), _item("milk", 1), _item("old", -1)], TODAY
        )
        risky = at_risk(entries)
        assert {e.item.name for e in risky} == {"milk", "old"}

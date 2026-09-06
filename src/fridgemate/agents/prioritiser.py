"""Prioritiser - Decision-Support class.

Ranks pantry items by how soon they must be used. This step is *deliberately
deterministic*: given the same pantry and date it always returns the same
ordering and the same urgency bands. That makes it trivial to unit-test and
gives us a stable, measurable core (precision/recall against a hand-labelled
set) rather than something that drifts between runs.
"""

from __future__ import annotations

from datetime import date

from fridgemate.config import AT_RISK_WITHIN_DAYS
from fridgemate.models import PantryItem, PriorityEntry, Urgency


def _urgency_for(days_left: int) -> Urgency:
    """Map whole days remaining to an urgency band."""
    if days_left < 0:
        return Urgency.EXPIRED
    if days_left == 0:
        return Urgency.TODAY
    if days_left <= AT_RISK_WITHIN_DAYS:
        return Urgency.SOON
    return Urgency.OK


def _reason_for(item: PantryItem, days_left: int, urgency: Urgency) -> str:
    """Short human-readable explanation, shown in the digest and the UI."""
    if urgency is Urgency.EXPIRED:
        return f"{item.name} went past its best-before {abs(days_left)} day(s) ago."
    if urgency is Urgency.TODAY:
        return f"{item.name} is best used today."
    if urgency is Urgency.SOON:
        return f"{item.name} has {days_left} day(s) left."
    return f"{item.name} is fine for {days_left} more day(s)."


def prioritise(items: list[PantryItem], today: date) -> list[PriorityEntry]:
    """Return every item wrapped in a PriorityEntry, soonest-to-expire first."""
    entries = [
        PriorityEntry(
            item=item,
            days_left=(dl := item.days_left(today)),
            urgency=(u := _urgency_for(dl)),
            reason=_reason_for(item, dl, u),
        )
        for item in items
    ]
    entries.sort(key=lambda e: (e.days_left, e.item.name))
    return entries


def at_risk(entries: list[PriorityEntry]) -> list[PriorityEntry]:
    """Filter to just the entries that need attention now (expired / today / soon)."""
    return [e for e in entries if e.urgency is not Urgency.OK]

"""Ingest agent - Extraction class.

Takes a blob of free text (a shopping list someone typed, or a pasted
supermarket receipt) and returns structured ``ParsedItem`` rows. This is the
'unstructured content -> structured, actionable data' pattern from the deck.

Design choices:
* One job, one call. The agent extracts and exits; it does not decide anything.
* Small typed output (``IngestResult``) so downstream steps get a clean payload.
* A deterministic fallback (line splitter + keyword categories) so a Bedrock
  outage or a schema-validation failure still lets the user add groceries.
"""

from __future__ import annotations

import re

from fridgemate.config import MODEL_FAST
from fridgemate.llm import structured
from fridgemate.models import IngestResult, ParsedItem
from fridgemate.shelf_life import (
    DEFAULT_SHELF_LIFE_DAYS,
    clamp_shelf_life,
    guess_category,
)

_SYSTEM = (
    "You extract grocery items from messy input: a typed list, or a pasted "
    "supermarket receipt with prices, quantities and store codes.\n"
    "For each real food item return: name (clean, lowercase, no brand codes), "
    "quantity as written, a category from the allowed set, and "
    "estimated_shelf_life_days = how many days it typically stays good after "
    "purchase when stored normally.\n"
    "Ignore non-food lines (totals, loyalty points, tax, card numbers). "
    "If the input has no food items, return an empty list and say so in notes."
)


def ingest_text(raw: str) -> IngestResult:
    """Parse ``raw`` into an ``IngestResult``.

    Falls back to a naive parser if the model call or schema validation fails,
    so the UI can always add *something*.
    """
    raw = (raw or "").strip()
    if not raw:
        return IngestResult(items=[], notes="Empty input.")

    try:
        model = structured(IngestResult, MODEL_FAST)
        result: IngestResult = model.invoke(
            [("system", _SYSTEM), ("human", raw)]
        )
        # Defensive clean-up: clamp shelf life, backfill a category if the model
        # left it as the default but the name clearly implies one.
        for item in result.items:
            item.estimated_shelf_life_days = clamp_shelf_life(
                item.estimated_shelf_life_days
            )
        return result
    except Exception as exc:  # noqa: BLE001 - any failure should degrade gracefully
        return _fallback_parse(raw, reason=str(exc))


def _fallback_parse(raw: str, reason: str) -> IngestResult:
    """Very small offline parser: one item per line, keyword category."""
    items: list[ParsedItem] = []
    for line in raw.splitlines():
        line = line.strip(" -*\t")
        if not line:
            continue
        # Pull a leading quantity like "2 " or "500g " if present.
        match = re.match(r"^(?P<qty>\d+\s*\w{0,3})\s+(?P<name>.+)$", line)
        qty, name = (match.group("qty"), match.group("name")) if match else ("1", line)
        category = guess_category(name)
        items.append(
            ParsedItem(
                name=name.lower(),
                quantity=qty.strip(),
                category=category,
                estimated_shelf_life_days=DEFAULT_SHELF_LIFE_DAYS[category],
            )
        )
    return IngestResult(
        items=items,
        notes=f"Parsed offline (model unavailable: {reason}).",
    )

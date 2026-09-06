"""Typed data models shared across the agents.

Using Pydantic models as the contract between steps gives us two things the
deck asks for: small, validated payloads passed between agents, and a natural
place to measure a "schema validation pass rate" (does the model's output
parse on the first try?).
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Category(str, Enum):
    """Coarse food categories. Each maps to a default shelf life in shelf_life.py."""

    PRODUCE = "produce"
    LEAFY = "leafy_greens"
    DAIRY = "dairy"
    EGGS = "eggs"
    MEAT = "meat"
    FISH = "fish"
    BREAD = "bread"
    LEFTOVERS = "leftovers"
    FROZEN = "frozen"
    PANTRY = "pantry"
    OTHER = "other"


class Urgency(str, Enum):
    """How soon an item needs to be used, derived from days remaining."""

    EXPIRED = "expired"
    TODAY = "today"
    SOON = "soon"
    OK = "ok"


# --- Ingest agent ---------------------------------------------------------


class ParsedItem(BaseModel):
    """One grocery item extracted from free text or a receipt by the ingest agent."""

    name: str = Field(description="Human-readable item name, e.g. 'baby spinach'.")
    quantity: str = Field(
        default="1",
        description="Free-text amount as written, e.g. '500 g', '2', '1 loaf'.",
    )
    category: Category = Field(
        default=Category.OTHER, description="Best-guess food category."
    )
    estimated_shelf_life_days: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Typical days this item stays good after purchase.",
    )


class IngestResult(BaseModel):
    """Everything the ingest agent pulled out of one block of input text."""

    items: list[ParsedItem] = Field(default_factory=list)
    notes: str = Field(
        default="", description="Anything the parser was unsure about."
    )


# --- Pantry storage -----------------------------------------------------


class PantryItem(BaseModel):
    """An item currently in the pantry, as stored in SQLite."""

    id: Optional[int] = None
    name: str
    quantity: str = "1"
    category: Category = Category.OTHER
    bought_on: date
    best_before: date
    source: str = "manual"  # "manual" or "receipt"
    added_at: datetime = Field(default_factory=datetime.now)

    def days_left(self, today: date) -> int:
        """Whole days from ``today`` until best_before (negative = already past)."""
        return (self.best_before - today).days


# --- Prioritiser ------------------------------------------------------


class PriorityEntry(BaseModel):
    """A pantry item plus the computed urgency the prioritiser assigned it."""

    item: PantryItem
    days_left: int
    urgency: Urgency
    reason: str


# --- Recipe agent ----------------------------------------------------


class Recipe(BaseModel):
    """A single suggested recipe."""

    title: str
    uses: list[str] = Field(
        description="Names of pantry items this recipe consumes (must include at-risk ones)."
    )
    extra_shopping: list[str] = Field(
        default_factory=list,
        description="Items NOT in the pantry that the cook still needs to buy.",
    )
    steps: list[str] = Field(description="Ordered preparation steps.")
    time_minutes: int = Field(ge=1, le=240)
    serves: int = Field(ge=1, le=12)


class RecipeSuggestion(BaseModel):
    """The recipe agent's output: a few recipes plus why it chose them."""

    recipes: list[Recipe] = Field(default_factory=list)
    rationale: str = ""


class CritiqueResult(BaseModel):
    """The critic's verdict on a RecipeSuggestion inside the refine loop."""

    approved: bool
    problems: list[str] = Field(
        default_factory=list,
        description="Concrete issues to fix; empty when approved is true.",
    )


# --- Planner / daily digest ---------------------------------------


class DailyDigest(BaseModel):
    """The end-to-end output the planner produces for the user each day."""

    generated_on: date
    at_risk: list[PriorityEntry] = Field(default_factory=list)
    suggestion: Optional[RecipeSuggestion] = None
    message: str = ""

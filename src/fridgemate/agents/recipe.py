"""Recipe agent - Creative/Generative class, with a bounded reflection loop.

Given the at-risk items and the rest of the pantry, draft 2-3 recipes that use
up the at-risk items. A second model call (the critic) checks the draft against
concrete rules; if it fails, the problems are fed back and the generator tries
again - up to ``MAX_RECIPE_REFINE_LOOPS`` times.

The cap is a plain counter here, not a model decision. A refine loop that only
exits 'when the critic is happy' can loop forever; this one cannot.
"""

from __future__ import annotations

from dataclasses import dataclass

from fridgemate.config import MAX_RECIPE_REFINE_LOOPS, MODEL_FAST, MODEL_SMART
from fridgemate.llm import structured
from fridgemate.models import (
    CritiqueResult,
    PantryItem,
    PriorityEntry,
    RecipeSuggestion,
)


@dataclass
class RecipeConstraints:
    """User-supplied limits for a suggestion run. Small, plain payload."""

    servings: int = 2
    max_time_minutes: int = 45
    diet: str = "none"  # e.g. "vegetarian", "halal", "none"
    preference_hints: str = "No feedback history yet."


_GEN_SYSTEM = (
    "You are a practical home-cooking assistant. Propose 2-3 recipes that use "
    "up the AT-RISK items before they spoil.\n"
    "Rules:\n"
    "- Every recipe must use at least one at-risk item.\n"
    "- Prefer ingredients already in the pantry. Anything not in the pantry "
    "goes in extra_shopping and should be short and common.\n"
    "- Respect the diet, serving count and time limit given.\n"
    "- Keep steps concise (one line each)."
)

_CRITIC_SYSTEM = (
    "You review recipe suggestions against hard rules and return approved + a "
    "list of concrete problems.\n"
    "Fail the suggestion if ANY recipe: (a) uses zero at-risk items, (b) lists "
    "a pantry item in extra_shopping, (c) breaks the stated diet, or (d) "
    "exceeds the time limit. Otherwise approve it."
)


def _pantry_lines(items: list[PantryItem]) -> str:
    return "\n".join(f"- {it.name} ({it.quantity})" for it in items) or "- (pantry is empty)"


def _at_risk_lines(entries: list[PriorityEntry]) -> str:
    return "\n".join(f"- {e.item.name}: {e.reason}" for e in entries) or "- (nothing at risk)"


def _generate(
    at_risk: list[PriorityEntry],
    pantry: list[PantryItem],
    constraints: RecipeConstraints,
    prior_problems: list[str],
) -> RecipeSuggestion:
    """One generation pass. ``prior_problems`` is empty on the first attempt."""
    fix_note = ""
    if prior_problems:
        fix_note = "\n\nYour previous attempt had these problems - fix them:\n" + "\n".join(
            f"- {p}" for p in prior_problems
        )

    human = (
        f"AT-RISK ITEMS (use these up):\n{_at_risk_lines(at_risk)}\n\n"
        f"REST OF PANTRY:\n{_pantry_lines(pantry)}\n\n"
        f"CONSTRAINTS: serves {constraints.servings}, "
        f"<= {constraints.max_time_minutes} min, diet: {constraints.diet}.\n"
        f"HOUSEHOLD HABITS: {constraints.preference_hints}"
        f"{fix_note}"
    )
    model = structured(RecipeSuggestion, MODEL_SMART)
    return model.invoke([("system", _GEN_SYSTEM), ("human", human)])


def _critique(
    suggestion: RecipeSuggestion,
    at_risk: list[PriorityEntry],
    pantry: list[PantryItem],
    constraints: RecipeConstraints,
) -> CritiqueResult:
    """Score a suggestion against the hard rules."""
    at_risk_names = {e.item.name.lower() for e in at_risk}
    pantry_names = {it.name.lower() for it in pantry}
    recipes_text = "\n\n".join(
        f"{r.title}\n  uses: {r.uses}\n  extra_shopping: {r.extra_shopping}\n"
        f"  time: {r.time_minutes} min"
        for r in suggestion.recipes
    )
    human = (
        f"AT-RISK NAMES: {sorted(at_risk_names)}\n"
        f"PANTRY NAMES: {sorted(pantry_names)}\n"
        f"DIET: {constraints.diet}   TIME LIMIT: {constraints.max_time_minutes} min\n\n"
        f"SUGGESTION:\n{recipes_text}"
    )
    model = structured(CritiqueResult, MODEL_FAST)
    return model.invoke([("system", _CRITIC_SYSTEM), ("human", human)])


def suggest_recipes(
    at_risk: list[PriorityEntry],
    pantry: list[PantryItem],
    constraints: RecipeConstraints | None = None,
) -> RecipeSuggestion:
    """Generate -> critique -> refine, bounded by ``MAX_RECIPE_REFINE_LOOPS``.

    Returns the last suggestion produced, whether or not the critic finally
    approved it, so the UI always has something to show. The rationale records
    how many rounds ran and the critic's final verdict.
    """
    constraints = constraints or RecipeConstraints()
    if not at_risk:
        return RecipeSuggestion(recipes=[], rationale="Nothing is at risk today.")

    problems: list[str] = []
    suggestion = RecipeSuggestion()

    for attempt in range(1, MAX_RECIPE_REFINE_LOOPS + 1):
        suggestion = _generate(at_risk, pantry, constraints, problems)
        verdict = _critique(suggestion, at_risk, pantry, constraints)
        if verdict.approved:
            suggestion.rationale = (
                f"Approved by critic after {attempt} round(s). "
                + suggestion.rationale
            )
            return suggestion
        problems = verdict.problems

    suggestion.rationale = (
        f"Returned after hitting the {MAX_RECIPE_REFINE_LOOPS}-round cap with "
        f"open critic notes: {problems}. " + suggestion.rationale
    )
    return suggestion

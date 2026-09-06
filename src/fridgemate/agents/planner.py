r"""Planner - Orchestration class, built as a LangGraph state machine.

This is the 'control tower' that produces the daily digest. It plans a short
sequence, runs the deterministic prioritiser, then *decides* whether the
generative recipe agent needs to run at all (skip it when nothing is at risk -
that saves a Sonnet call), and finally composes the message.

    load_pantry -> prioritise -> (decide) --at risk--> suggest_recipes -> compose
                                          \--nothing--------------------/

The graph is small on purpose. Each node does one thing and writes one slice
of state.
"""

from __future__ import annotations

from datetime import date
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from fridgemate.agents.prioritiser import at_risk as filter_at_risk
from fridgemate.agents.prioritiser import prioritise
from fridgemate.agents.recipe import RecipeConstraints, suggest_recipes
from fridgemate.memory import FeedbackStore
from fridgemate.models import DailyDigest, PriorityEntry, RecipeSuggestion
from fridgemate.storage import PantryStore


class DigestState(TypedDict, total=False):
    """Working state threaded through the graph."""

    today: date
    constraints: RecipeConstraints
    ranked: list[PriorityEntry]
    at_risk: list[PriorityEntry]
    suggestion: RecipeSuggestion
    digest: DailyDigest


def _load_pantry(state: DigestState) -> DigestState:
    store = PantryStore()
    ranked = prioritise(store.list_items(), state["today"])
    return {"ranked": ranked}


def _prioritise(state: DigestState) -> DigestState:
    risky = filter_at_risk(state["ranked"])
    return {"at_risk": risky}


def _needs_recipes(state: DigestState) -> str:
    """Conditional edge: only call the generative agent when there is something to save."""
    return "suggest" if state.get("at_risk") else "compose"


def _suggest_recipes(state: DigestState) -> DigestState:
    pantry = [entry.item for entry in state["ranked"]]
    suggestion = suggest_recipes(
        state["at_risk"], pantry, state.get("constraints")
    )
    return {"suggestion": suggestion}


def _compose(state: DigestState) -> DigestState:
    risky = state.get("at_risk", [])
    suggestion = state.get("suggestion")

    if not risky:
        message = "Nothing in the pantry is close to expiring. Nice."
    else:
        names = ", ".join(e.item.name for e in risky)
        lead = f"{len(risky)} item(s) need using soon: {names}."
        if suggestion and suggestion.recipes:
            titles = "; ".join(r.title for r in suggestion.recipes)
            message = f"{lead} Suggested tonight: {titles}."
        else:
            message = f"{lead} No recipe matched the constraints this run."

    digest = DailyDigest(
        generated_on=state["today"],
        at_risk=risky,
        suggestion=suggestion,
        message=message,
    )
    return {"digest": digest}


def build_graph():
    """Compile and return the digest graph. Call ``.invoke({...})`` on the result."""
    graph = StateGraph(DigestState)
    graph.add_node("load_pantry", _load_pantry)
    graph.add_node("prioritise", _prioritise)
    graph.add_node("suggest_recipes", _suggest_recipes)
    graph.add_node("compose", _compose)

    graph.add_edge(START, "load_pantry")
    graph.add_edge("load_pantry", "prioritise")
    graph.add_conditional_edges(
        "prioritise",
        _needs_recipes,
        {"suggest": "suggest_recipes", "compose": "compose"},
    )
    graph.add_edge("suggest_recipes", "compose")
    graph.add_edge("compose", END)
    return graph.compile()


def run_daily_digest(
    today: date | None = None,
    constraints: RecipeConstraints | None = None,
) -> DailyDigest:
    """Run the whole graph once and return the digest.

    Pulls household preference hints from the feedback store so repeated runs
    adapt to what the user actually cooks.
    """
    today = today or date.today()
    constraints = constraints or RecipeConstraints()
    constraints.preference_hints = FeedbackStore().preference_hints()

    result = build_graph().invoke({"today": today, "constraints": constraints})
    return result["digest"]

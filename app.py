"""FridgeMate Streamlit UI.

Run with:  streamlit run app.py

Three panels:
* left  - add groceries (manual entry, or paste a receipt for the ingest agent)
* main  - the pantry, ranked by urgency
* main  - "Run daily digest" fires the LangGraph planner and shows recipes
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# Streamlit runs this file directly, so make the package under src/ importable.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import streamlit as st

from fridgemate.agents.planner import run_daily_digest
from fridgemate.agents.prioritiser import prioritise
from fridgemate.agents.recipe import RecipeConstraints
from fridgemate.memory import FeedbackStore
from fridgemate.models import Urgency
from fridgemate.pantry_service import add_from_text, add_manual
from fridgemate.storage import PantryStore

st.set_page_config(page_title="FridgeMate", page_icon="🥕", layout="wide")

store = PantryStore()
feedback = FeedbackStore()

_URGENCY_ICON = {
    Urgency.EXPIRED: "⛔",
    Urgency.TODAY: "🔴",
    Urgency.SOON: "🟠",
    Urgency.OK: "🟢",
}

# --- Sidebar: add groceries -------------------------------------------------

with st.sidebar:
    st.header("Add groceries")

    with st.form("manual_add", clear_on_submit=True):
        st.caption("Manual entry")
        name = st.text_input("Item")
        qty = st.text_input("Quantity", value="1")
        bought = st.date_input("Bought on", value=date.today())
        if st.form_submit_button("Add item") and name.strip():
            item = add_manual(name, qty, bought, store=store)
            st.success(f"Added {item.name} (best before {item.best_before}).")

    with st.form("receipt_add", clear_on_submit=True):
        st.caption("Paste a receipt or a list - the ingest agent parses it")
        raw = st.text_area("Receipt / list text", height=160)
        bought_r = st.date_input("Purchase date", value=date.today(), key="receipt_date")
        if st.form_submit_button("Parse and add") and raw.strip():
            with st.spinner("Extracting items..."):
                written = add_from_text(raw, bought_r, store=store)
            st.success(f"Added {len(written)} item(s).")
            for it in written:
                st.write(f"- {it.name} ({it.quantity}) -> {it.best_before}")

    if st.button("Reset pantry", type="secondary"):
        store.clear()
        st.rerun()

# --- Main: pantry table ---------------------------------------------------

st.title("🥕 FridgeMate")
st.caption("Eat what you have, before it goes off.")

items = store.list_items()
ranked = prioritise(items, date.today())

left, right = st.columns([1, 1], gap="large")

with left:
    st.subheader(f"Pantry ({len(items)} items)")
    if not ranked:
        st.info("Pantry is empty. Add something from the sidebar.")
    for entry in ranked:
        icon_col, body_col, action_col = st.columns(
            [1, 9, 2], vertical_alignment="center"
        )
        icon_col.write(_URGENCY_ICON[entry.urgency])
        body_col.write(f"**{entry.item.name}** · {entry.item.quantity}")
        body_col.caption(entry.reason)
        if action_col.button("🗑️", key=f"rm_{entry.item.id}", help="Remove"):
            store.remove_item(entry.item.id)
            st.rerun()

# --- Main: daily digest -------------------------------------------------

with right:
    st.subheader("Daily digest")
    st.caption("Runs the planner: prioritise → decide → suggest → compose")

    servings = st.slider("Servings", 1, 8, 2)
    max_time = st.slider("Max cook time (min)", 10, 120, 45, step=5)
    diet = st.selectbox("Diet", ["none", "vegetarian", "vegan", "halal", "pescatarian"])

    if st.button("Run daily digest", type="primary"):
        with st.spinner("Planning..."):
            digest = run_daily_digest(
                constraints=RecipeConstraints(
                    servings=servings, max_time_minutes=max_time, diet=diet
                )
            )
        st.session_state["digest"] = digest

    digest = st.session_state.get("digest")
    if digest:
        st.write(f"**{digest.message}**")
        if digest.suggestion:
            st.caption(digest.suggestion.rationale)
            for r in digest.suggestion.recipes:
                with st.expander(f"{r.title}  ·  {r.time_minutes} min  ·  serves {r.serves}"):
                    st.write("**Uses:** " + ", ".join(r.uses))
                    if r.extra_shopping:
                        st.write("**Also buy:** " + ", ".join(r.extra_shopping))
                    for i, step in enumerate(r.steps, 1):
                        st.write(f"{i}. {step}")
                    fb_cols = st.columns(2)
                    if fb_cols[0].button(
                        "Cooked it", key=f"cook_{r.title}", use_container_width=True
                    ):
                        for used in r.uses:
                            feedback.record(used, "cooked", r.title)
                        st.toast("Logged - future suggestions will lean this way.")
                    if fb_cols[1].button(
                        "Skipped", key=f"skip_{r.title}", use_container_width=True
                    ):
                        for used in r.uses:
                            feedback.record(used, "skipped", r.title)
                        st.toast("Noted.")

"""FridgeMate: an agentic pantry assistant that plans, acts, and adapts.

The package is organised so each agent does one small job and exits (see
``docs/architecture.md``):

* ``agents.ingest``      - turns free text / a pasted receipt into structured items
* ``agents.prioritiser`` - ranks items by how soon they expire (deterministic)
* ``agents.recipe``      - drafts recipes that use up at-risk items, with a critic loop
* ``agents.planner``     - the LangGraph orchestrator that produces the daily digest
"""

__version__ = "0.1.0"

"""nowcast: component-level CPI/PPI/PCE index math, bridge, and validation.

Deterministic by rule: no network calls, no LLM calls anywhere in this package
(CLAUDE.md rule 4). All historical data access goes through timebase.asof()
once it exists (Session 2A).
"""

__version__ = "0.1.0"

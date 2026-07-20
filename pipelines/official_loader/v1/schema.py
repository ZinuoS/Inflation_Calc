"""SourceRow/TargetRow for official_current (Session 2B, Group C).

CURRENT-history official series (CPI/PPI components, BEA PCE detail) for methodology
replication in 3A/3B -- NOT backtest targets (those stay on ALFRED vintages). period
is a real date; value a float; the rest strings. seasonal = SA|NSA.
"""
import datetime as dt
from pydantic import BaseModel

class SourceRow(BaseModel):
    source: str
    series_id: str
    item_code: str
    seasonal: str
    frequency: str
    period: str
    value: str

class TargetRow(BaseModel):
    source: str
    series_id: str
    item_code: str
    seasonal: str
    frequency: str
    period: dt.date
    value: float

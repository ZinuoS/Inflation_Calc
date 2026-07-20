"""SourceRow/TargetRow for cpi_weights (BLS relative-importance, vintaged by year).

BLS Handbook of Methods, CPI ch. 17 (weights): relative importances are updated
annually; a backtest for year Y must use year-Y weights. weight_year is the calendar
year the weights were in effect; item_code joins the CPI component map.
"""
from pydantic import BaseModel

class SourceRow(BaseModel):
    weight_year: str
    item_code: str
    weight_cpi_u: str
    weight_cpi_w: str

class TargetRow(BaseModel):
    weight_year: int
    item_code: str
    weight_cpi_u: float
    weight_cpi_w: float

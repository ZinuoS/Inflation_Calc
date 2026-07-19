"""SourceRow/TargetRow for the shared proxy_observations loader.

The uniform contract every proxy source normalizes into at the edge. period is a
real date (first-of-month for monthly, week-ending for weekly); value a float;
the rest stay strings. vintage_status carries the Amendment-1 classification
(point_in_time | unrevised | revised_latest_only) into reconciliation.
"""

import datetime as dt

from pydantic import BaseModel


class SourceRow(BaseModel):
    source: str
    series_key: str
    frequency: str
    period: str
    value: str
    vintage_status: str
    observed_date: str


class TargetRow(BaseModel):
    source: str
    series_key: str
    frequency: str
    period: dt.date
    value: float
    vintage_status: str
    observed_date: str

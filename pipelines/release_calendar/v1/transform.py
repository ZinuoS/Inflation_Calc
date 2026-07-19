"""Transform for release_calendar v1.

Composed only from naru.ops (restricted namespace: no imports). The CSV arrives
with every cell a string; the two date columns are coerced to ISO dates, the
rest pass through as declared strings. All the messy work (fetch, dedup, mapping)
happened deterministically at the edge in ../fetch.py and is frozen in the CSV.
"""

COLUMN_NAMES = [
    "print",
    "reference_period",
    "reference_period_basis",
    "release_date",
    "release_datetime_et",
    "release_time_basis",
    "source_url",
]


def transform(raw_grid):
    df = ops.promote_header(raw_grid, header_row=1, column_names=COLUMN_NAMES)
    df = ops.drop_empty(df)
    df = ops.coerce_date(df, "reference_period", fmt="%Y-%m-%d")
    df = ops.coerce_date(df, "release_date", fmt="%Y-%m-%d")
    return df[[*COLUMN_NAMES, "_src_row"]]

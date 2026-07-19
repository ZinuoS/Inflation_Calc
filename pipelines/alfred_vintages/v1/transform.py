"""Transform for alfred_vintages v1.

naru.ops only (no imports). reference_period and observed_asof_vintage become
ISO dates; value becomes float; series_id/mapping_series_id/vintage_end pass
through as strings. vintage_end is deliberately NOT coerced to a date -- open
vintages carry 9999-12-31, beyond pandas Timestamp range.
"""

COLUMN_NAMES = [
    "series_id",
    "mapping_series_id",
    "reference_period",
    "observed_asof_vintage",
    "vintage_end",
    "value",
]


def transform(raw_grid):
    df = ops.promote_header(raw_grid, header_row=1, column_names=COLUMN_NAMES)
    df = ops.drop_empty(df)
    df = ops.coerce_date(df, "reference_period", fmt="%Y-%m-%d")
    df = ops.coerce_date(df, "observed_asof_vintage", fmt="%Y-%m-%d")
    df = ops.coerce_numeric(df, "value")
    return df[[*COLUMN_NAMES, "_src_row"]]

"""Transform for the shared proxy_observations loader (naru.ops only)."""

COLUMN_NAMES = ["source", "series_key", "frequency", "period", "value", "vintage_status", "observed_date"]


def transform(raw_grid):
    df = ops.promote_header(raw_grid, header_row=1, column_names=COLUMN_NAMES)
    df = ops.drop_empty(df)
    df = ops.coerce_date(df, "period", fmt="%Y-%m-%d")
    df = ops.coerce_numeric(df, "value")
    return df[[*COLUMN_NAMES, "_src_row"]]

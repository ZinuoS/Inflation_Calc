"""Transform for official_loader (naru.ops only)."""
COLUMN_NAMES = ["source","series_id","item_code","seasonal","frequency","period","value"]
def transform(raw_grid):
    df = ops.promote_header(raw_grid, header_row=1, column_names=COLUMN_NAMES)
    df = ops.drop_empty(df)
    df = ops.coerce_date(df, "period", fmt="%Y-%m-%d")
    df = ops.coerce_numeric(df, "value")
    return df[[*COLUMN_NAMES, "_src_row"]]

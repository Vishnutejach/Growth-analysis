from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import FUNNEL_STAGES, SOURCE_DATA_PATH


def load_marketing_funnel_data(source_path: Path = SOURCE_DATA_PATH) -> pd.DataFrame:
    if not source_path.exists():
        raise FileNotFoundError(f"Source dataset not found: {source_path}")

    df = pd.read_csv(source_path)
    df.columns = [column.strip().lower() for column in df.columns]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["order_value"] = pd.to_numeric(df["order_value"], errors="coerce").fillna(0)
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0)

    for column in FUNNEL_STAGES + ["discount_applied"]:
        df[f"{column}_flag"] = df[column].astype(str).str.lower().eq("yes").astype(int)

    df["is_purchaser_session"] = df["purchase_completed_flag"].eq(1)
    return df.dropna(subset=["date"]).copy()

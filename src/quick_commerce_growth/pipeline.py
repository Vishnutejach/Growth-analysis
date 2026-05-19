from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import PROCESSED_DATA_DIR, RAW_DATA_DIR, SOURCE_DATA_PATH
from .data_loading import load_marketing_funnel_data
from .metrics import (
    build_campaign_performance,
    build_dimension_performance,
    build_funnel_summary,
    build_monthly_summary,
    build_retention_summary,
)


def _ensure_directories() -> None:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _write_run_summary(
    path: Path,
    df: pd.DataFrame,
    funnel_df: pd.DataFrame,
    retention_df: pd.DataFrame,
    campaign_df: pd.DataFrame,
) -> None:
    orders = int(df["purchase_completed_flag"].sum())
    revenue = float(df["revenue"].sum())
    sessions = len(df)
    best_campaign = campaign_df.iloc[0]
    lines = [
        "Quick-Commerce Growth Command Center Run Summary",
        f"Source: {SOURCE_DATA_PATH}",
        f"Date range: {df['date'].min().date()} to {df['date'].max().date()}",
        f"Sessions: {sessions:,}",
        f"Users: {df['user_id'].nunique():,}",
        f"Orders: {orders:,}",
        f"Revenue: {revenue:,.2f}",
        f"Visit-to-order conversion: {orders / sessions:.2%}",
        f"First-to-second order rate: {retention_df.loc[0, 'first_to_second_order_rate']:.2%}",
        f"D7/D14/D30 retention: {retention_df.loc[0, 'd7_retention']:.2%} / {retention_df.loc[0, 'd14_retention']:.2%} / {retention_df.loc[0, 'd30_retention']:.2%}",
        f"Highest revenue campaign: {best_campaign['channel']} - {best_campaign['campaign_type']} ({best_campaign['revenue']:,.2f})",
        f"Biggest funnel dropoff: {funnel_df.sort_values('dropoff_from_previous', ascending=False).iloc[0]['stage']}",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def run_pipeline() -> None:
    _ensure_directories()

    raw_df = load_marketing_funnel_data()
    raw_df.to_csv(RAW_DATA_DIR / "d2c_marketing_funnel_clean.csv", index=False)

    funnel_df = build_funnel_summary(raw_df)
    monthly_df = build_monthly_summary(raw_df)
    dimension_df = build_dimension_performance(raw_df)
    campaign_df = build_campaign_performance(raw_df)
    retention_summary_df, customer_retention_df = build_retention_summary(raw_df)

    funnel_df.to_csv(PROCESSED_DATA_DIR / "funnel_summary.csv", index=False)
    monthly_df.to_csv(PROCESSED_DATA_DIR / "monthly_growth_kpis.csv", index=False)
    dimension_df.to_csv(PROCESSED_DATA_DIR / "segment_wallet_share.csv", index=False)
    campaign_df.to_csv(PROCESSED_DATA_DIR / "campaign_performance.csv", index=False)
    retention_summary_df.to_csv(PROCESSED_DATA_DIR / "retention_summary.csv", index=False)
    customer_retention_df.to_csv(PROCESSED_DATA_DIR / "customer_retention_churn.csv", index=False)

    _write_run_summary(
        PROCESSED_DATA_DIR / "run_summary.txt",
        raw_df,
        funnel_df,
        retention_summary_df,
        campaign_df,
    )

    print("Quick-commerce growth pipeline completed successfully.")
    print(f"Sessions: {len(raw_df):,}")
    print(f"Users: {raw_df['user_id'].nunique():,}")
    print(f"Orders: {int(raw_df['purchase_completed_flag'].sum()):,}")
    print(f"Revenue: {raw_df['revenue'].sum():,.2f}")
    print(
        "D7/D14/D30 retention: "
        f"{retention_summary_df.loc[0, 'd7_retention']:.2%} / "
        f"{retention_summary_df.loc[0, 'd14_retention']:.2%} / "
        f"{retention_summary_df.loc[0, 'd30_retention']:.2%}"
    )

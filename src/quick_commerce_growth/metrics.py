from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DIMENSIONS, FUNNEL_STAGES


STAGE_LABELS = {
    "visited_website": "Install / Visit",
    "viewed_product": "Signup / Product View",
    "added_to_cart": "Cart Add",
    "checkout_started": "Checkout",
    "purchase_completed": "First Order / Purchase",
}


def safe_rate(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def build_funnel_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    previous_count = None
    first_count = int(df[f"{FUNNEL_STAGES[0]}_flag"].sum())

    for index, stage in enumerate(FUNNEL_STAGES, start=1):
        count = int(df[f"{stage}_flag"].sum())
        rows.append(
            {
                "stage_order": index,
                "stage": STAGE_LABELS[stage],
                "sessions": count,
                "conversion_from_previous": safe_rate(count, previous_count or count),
                "conversion_from_visit": safe_rate(count, first_count),
                "dropoff_from_previous": 1 - safe_rate(count, previous_count or count),
            }
        )
        previous_count = count

    return pd.DataFrame(rows)


def build_monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby("month", as_index=False).agg(
        sessions=("session_id", "count"),
        users=("user_id", "nunique"),
        product_views=("viewed_product_flag", "sum"),
        cart_adds=("added_to_cart_flag", "sum"),
        checkouts=("checkout_started_flag", "sum"),
        orders=("purchase_completed_flag", "sum"),
        revenue=("revenue", "sum"),
        discounted_sessions=("discount_applied_flag", "sum"),
    )
    grouped["visit_to_order_rate"] = grouped.apply(
        lambda row: safe_rate(row["orders"], row["sessions"]), axis=1
    )
    grouped["aov"] = grouped.apply(lambda row: safe_rate(row["revenue"], row["orders"]), axis=1)
    grouped["discount_usage_rate"] = grouped.apply(
        lambda row: safe_rate(row["discounted_sessions"], row["sessions"]), axis=1
    )
    return grouped.sort_values("month")


def build_dimension_performance(df: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for dimension in DIMENSIONS:
        grouped = df.groupby(dimension, as_index=False).agg(
            sessions=("session_id", "count"),
            users=("user_id", "nunique"),
            views=("viewed_product_flag", "sum"),
            carts=("added_to_cart_flag", "sum"),
            checkouts=("checkout_started_flag", "sum"),
            orders=("purchase_completed_flag", "sum"),
            revenue=("revenue", "sum"),
            discounted_sessions=("discount_applied_flag", "sum"),
        )
        grouped.insert(0, "dimension", dimension)
        grouped = grouped.rename(columns={dimension: "segment"})
        frames.append(grouped)

    output = pd.concat(frames, ignore_index=True)
    output["conversion_rate"] = output.apply(lambda row: safe_rate(row["orders"], row["sessions"]), axis=1)
    output["view_to_cart_rate"] = output.apply(lambda row: safe_rate(row["carts"], row["views"]), axis=1)
    output["checkout_to_order_rate"] = output.apply(lambda row: safe_rate(row["orders"], row["checkouts"]), axis=1)
    output["aov"] = output.apply(lambda row: safe_rate(row["revenue"], row["orders"]), axis=1)
    output["wallet_share"] = output["revenue"] / output.groupby("dimension")["revenue"].transform("sum")
    return output.sort_values(["dimension", "revenue"], ascending=[True, False])


def build_campaign_performance(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby(["channel", "campaign_type"], as_index=False).agg(
        sessions=("session_id", "count"),
        users=("user_id", "nunique"),
        carts=("added_to_cart_flag", "sum"),
        checkouts=("checkout_started_flag", "sum"),
        orders=("purchase_completed_flag", "sum"),
        revenue=("revenue", "sum"),
        discounted_sessions=("discount_applied_flag", "sum"),
    )
    grouped["conversion_rate"] = grouped.apply(lambda row: safe_rate(row["orders"], row["sessions"]), axis=1)
    grouped["revenue_per_session"] = grouped.apply(lambda row: safe_rate(row["revenue"], row["sessions"]), axis=1)
    grouped["discount_usage_rate"] = grouped.apply(
        lambda row: safe_rate(row["discounted_sessions"], row["sessions"]), axis=1
    )
    grouped["wallet_share"] = grouped["revenue"] / grouped["revenue"].sum()
    return grouped.sort_values("revenue", ascending=False)


def build_retention_summary(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    purchases = df[df["purchase_completed_flag"].eq(1)].sort_values(["user_id", "date", "session_id"]).copy()
    if purchases.empty:
        empty = pd.DataFrame()
        return empty, empty

    user_orders = purchases.groupby("user_id").agg(
        first_order_date=("date", "min"),
        last_order_date=("date", "max"),
        order_count=("session_id", "count"),
        customer_revenue=("revenue", "sum"),
    )

    def second_order_date(dates: pd.Series) -> pd.Timestamp | pd.NaT:
        sorted_dates = dates.sort_values()
        return sorted_dates.iloc[1] if len(sorted_dates) > 1 else pd.NaT

    user_orders["second_order_date"] = purchases.groupby("user_id")["date"].apply(second_order_date)
    user_orders["days_to_second_order"] = (
        user_orders["second_order_date"] - user_orders["first_order_date"]
    ).dt.days

    analysis_end = df["date"].max()
    user_orders["days_since_last_order"] = (analysis_end - user_orders["last_order_date"]).dt.days
    user_orders["repeat_buyer_flag"] = user_orders["order_count"].gt(1).astype(int)
    user_orders["retained_d7"] = user_orders["days_to_second_order"].between(0, 7, inclusive="both").astype(int)
    user_orders["retained_d14"] = user_orders["days_to_second_order"].between(0, 14, inclusive="both").astype(int)
    user_orders["retained_d30"] = user_orders["days_to_second_order"].between(0, 30, inclusive="both").astype(int)
    user_orders["repeat_purchase_frequency"] = np.where(
        user_orders["order_count"].gt(1),
        user_orders["order_count"]
        / np.maximum((user_orders["last_order_date"] - user_orders["first_order_date"]).dt.days / 30, 1),
        0,
    )
    user_orders["churn_risk"] = pd.cut(
        user_orders["days_since_last_order"],
        bins=[-1, 14, 30, np.inf],
        labels=["Low", "Medium", "High"],
    ).astype(str)

    summary = pd.DataFrame(
        [
            {
                "purchasers": int(len(user_orders)),
                "repeat_buyers": int(user_orders["repeat_buyer_flag"].sum()),
                "first_to_second_order_rate": safe_rate(user_orders["repeat_buyer_flag"].sum(), len(user_orders)),
                "d7_retention": safe_rate(user_orders["retained_d7"].sum(), len(user_orders)),
                "d14_retention": safe_rate(user_orders["retained_d14"].sum(), len(user_orders)),
                "d30_retention": safe_rate(user_orders["retained_d30"].sum(), len(user_orders)),
                "avg_repeat_purchase_frequency": float(user_orders["repeat_purchase_frequency"].mean()),
                "high_churn_risk_customers": int(user_orders["churn_risk"].eq("High").sum()),
                "high_churn_risk_rate": safe_rate(user_orders["churn_risk"].eq("High").sum(), len(user_orders)),
            }
        ]
    )

    return summary, user_orders.reset_index()

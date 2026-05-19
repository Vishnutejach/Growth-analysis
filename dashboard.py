from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


st.set_page_config(page_title="Quick-Commerce Growth Command Center", layout="wide")


@st.cache_data
def load_outputs() -> dict[str, pd.DataFrame]:
    return {
        "funnel": pd.read_csv(PROCESSED_DIR / "funnel_summary.csv"),
        "monthly": pd.read_csv(PROCESSED_DIR / "monthly_growth_kpis.csv"),
        "segments": pd.read_csv(PROCESSED_DIR / "segment_wallet_share.csv"),
        "campaigns": pd.read_csv(PROCESSED_DIR / "campaign_performance.csv"),
        "retention": pd.read_csv(PROCESSED_DIR / "retention_summary.csv"),
        "customers": pd.read_csv(PROCESSED_DIR / "customer_retention_churn.csv"),
    }


def pct(value: float) -> str:
    return f"{value:.1%}"


def money(value: float) -> str:
    return f"₹{value:,.0f}"


data = load_outputs()
funnel = data["funnel"]
monthly = data["monthly"]
segments = data["segments"]
campaigns = data["campaigns"]
retention = data["retention"].iloc[0]
customers = data["customers"]

st.title("Quick-Commerce Growth Command Center")

selected_months = st.sidebar.multiselect(
    "Month",
    options=monthly["month"].tolist(),
    default=monthly["month"].tolist(),
)
selected_dimension = st.sidebar.selectbox(
    "Wallet share view",
    options=["channel", "campaign_type", "device", "region", "user_type"],
)

filtered_monthly = monthly[monthly["month"].isin(selected_months)]
if filtered_monthly.empty:
    st.warning("Select at least one month to view the command center.")
    st.stop()

sessions = int(filtered_monthly["sessions"].sum())
orders = int(filtered_monthly["orders"].sum())
revenue = float(filtered_monthly["revenue"].sum())
conversion = orders / sessions if sessions else 0
aov = revenue / orders if orders else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Sessions", f"{sessions:,}")
col2.metric("Orders", f"{orders:,}")
col3.metric("Revenue", money(revenue))
col4.metric("Visit to order", pct(conversion))
col5.metric("AOV", money(aov))

left, right = st.columns([1.05, 1])
with left:
    st.subheader("Acquisition to first order funnel")
    fig = px.funnel(
        funnel,
        x="sessions",
        y="stage",
        text="conversion_from_visit",
        color_discrete_sequence=["#2563eb"],
    )
    fig.update_traces(texttemplate="%{text:.1%} of visits")
    fig.update_layout(height=390, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Monthly growth")
    monthly_long = filtered_monthly.melt(
        id_vars="month",
        value_vars=["sessions", "orders"],
        var_name="metric",
        value_name="value",
    )
    fig = px.bar(
        monthly_long,
        x="month",
        y="value",
        color="metric",
        barmode="group",
        color_discrete_map={"sessions": "#64748b", "orders": "#16a34a"},
    )
    fig.update_layout(height=390, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

r1, r2, r3, r4, r5 = st.columns(5)
r1.metric("First to second order", pct(retention["first_to_second_order_rate"]))
r2.metric("D7 retention", pct(retention["d7_retention"]))
r3.metric("D14 retention", pct(retention["d14_retention"]))
r4.metric("D30 retention", pct(retention["d30_retention"]))
r5.metric("High churn risk", pct(retention["high_churn_risk_rate"]))

left, right = st.columns(2)
with left:
    st.subheader("Campaign performance")
    fig = px.scatter(
        campaigns,
        x="conversion_rate",
        y="revenue_per_session",
        size="sessions",
        color="channel",
        hover_data=["campaign_type", "orders", "revenue"],
        labels={
            "conversion_rate": "Conversion rate",
            "revenue_per_session": "Revenue per session",
        },
    )
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Wallet share")
    wallet = segments[segments["dimension"].eq(selected_dimension)].sort_values(
        "wallet_share", ascending=False
    )
    fig = px.bar(
        wallet,
        x="wallet_share",
        y="segment",
        orientation="h",
        color="conversion_rate",
        color_continuous_scale="Tealgrn",
        labels={"wallet_share": "Revenue share", "segment": ""},
    )
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=20, b=10), yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Churn risk and lifecycle interventions")
churn_table = (
    customers.groupby("churn_risk", as_index=False)
    .agg(
        customers=("user_id", "nunique"),
        revenue=("customer_revenue", "sum"),
        avg_orders=("order_count", "mean"),
        avg_days_since_last_order=("days_since_last_order", "mean"),
    )
    .sort_values("customers", ascending=False)
)
st.dataframe(
    churn_table,
    use_container_width=True,
    hide_index=True,
    column_config={
        "revenue": st.column_config.NumberColumn("Revenue", format="₹%.0f"),
        "avg_orders": st.column_config.NumberColumn("Avg orders", format="%.2f"),
        "avg_days_since_last_order": st.column_config.NumberColumn("Avg days since last order", format="%.1f"),
    },
)

st.subheader("Top campaign table")
st.dataframe(
    campaigns.head(20),
    use_container_width=True,
    hide_index=True,
    column_config={
        "conversion_rate": st.column_config.ProgressColumn("Conversion", format="%.1f", min_value=0, max_value=1),
        "wallet_share": st.column_config.ProgressColumn("Wallet share", format="%.1f", min_value=0, max_value=1),
        "revenue": st.column_config.NumberColumn("Revenue", format="₹%.0f"),
        "revenue_per_session": st.column_config.NumberColumn("Revenue/session", format="₹%.2f"),
    },
)

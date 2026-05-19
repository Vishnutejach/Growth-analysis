# Growth Analysis: Quick-Commerce Growth Command Center

An end-to-end SQL + Python + Streamlit analytics project for diagnosing a D2C grocery/quick-commerce marketing funnel. The dashboard tracks acquisition quality, activation leakage, campaign performance, repeat purchase behavior, retention, and churn risk from session-level funnel data.

## Why This Project Matters

Quick-commerce growth teams do not only need top-line sessions and revenue. They need to know where users fall out of the funnel, which campaigns create high-intent customers, how many first-time buyers return, and which customer cohorts need onboarding, habit-formation, or win-back interventions.

This repository turns raw funnel events into a decision-ready growth command center.

## Dataset

The project uses a real CSV dataset included at:

`data/raw/d2c_marketing_funnel_data.csv`

Each row represents a user session with acquisition, funnel, and revenue attributes:

| Field Group | Columns |
| --- | --- |
| Identity | `user_id`, `session_id` |
| Time | `date`, `month` |
| Acquisition | `channel`, `campaign_type`, `device`, `region`, `user_type` |
| Funnel Events | `visited_website`, `viewed_product`, `added_to_cart`, `checkout_started`, `purchase_completed` |
| Monetization | `discount_applied`, `order_value`, `revenue` |

The dataset does not include SKU or product category, so the dashboard models wallet share across available business segments: channel, campaign type, device, region, and user type.

## Core KPIs

- Visit/install to product-view conversion
- Product-view to cart-add conversion
- Cart-add to checkout conversion
- Checkout to first-order conversion
- First-order to second-order rate
- D7, D14, and D30 retention
- Repeat purchase frequency
- Churn-risk bands based on days since last order
- Segment wallet share
- Campaign conversion, revenue per session, and discount usage

## Repository Structure

```text
.
|-- dashboard.py
|-- README.md
|-- requirements.txt
|-- run_pipeline.py
|-- data
|   |-- raw
|   |   `-- d2c_marketing_funnel_data.csv
|   `-- processed
|       |-- campaign_performance.csv
|       |-- customer_retention_churn.csv
|       |-- funnel_summary.csv
|       |-- monthly_growth_kpis.csv
|       |-- retention_summary.csv
|       |-- run_summary.txt
|       `-- segment_wallet_share.csv
|-- sql
|   |-- schema.sql
|   `-- kpi_queries.sql
`-- src
    `-- quick_commerce_growth
        |-- config.py
        |-- data_loading.py
        |-- metrics.py
        `-- pipeline.py
```

## Quick Start

Create an environment and install dependencies:

```bash
pip install -r requirements.txt
```

Generate the analytics tables:

```bash
python run_pipeline.py
```

Launch the Streamlit dashboard:

```bash
streamlit run dashboard.py
```

If you want to use a different source CSV, set:

```bash
D2C_FUNNEL_DATA_PATH=/path/to/your/file.csv python run_pipeline.py
```

On Windows PowerShell:

```powershell
$env:D2C_FUNNEL_DATA_PATH="C:\path\to\your\file.csv"
python run_pipeline.py
```

## Pipeline Outputs

Running `run_pipeline.py` creates these dashboard-ready tables:

| Output | Purpose |
| --- | --- |
| `funnel_summary.csv` | Stage-by-stage funnel volume, conversion, and drop-off |
| `monthly_growth_kpis.csv` | Monthly sessions, users, orders, revenue, AOV, and conversion |
| `campaign_performance.csv` | Channel and campaign performance diagnostics |
| `segment_wallet_share.csv` | Revenue share and conversion by business segment |
| `retention_summary.csv` | First-to-second order, D7/D14/D30 retention, churn summary |
| `customer_retention_churn.csv` | Customer-level order frequency and churn-risk table |
| `run_summary.txt` | Executive text summary of the latest pipeline run |

## Latest Run Snapshot

From the included dataset:

- Sessions: **120,000**
- Users: **112,352**
- Orders: **8,181**
- Revenue: **17,016,599.15**
- Visit-to-order conversion: **6.82%**
- First-to-second order rate: **0.52%**
- Biggest funnel drop-off: **Cart Add**
- Highest revenue campaign: **Paid Ads - Discount**

## SQL Layer

The `sql` folder contains warehouse-style analytics assets:

- `schema.sql`: table definition and CSV load pattern
- `kpi_queries.sql`: executive KPIs, funnel progression, monthly trends, campaign performance, wallet share, and retention queries

These queries are written in DuckDB/Postgres-style SQL and can be adapted for BI tools such as Metabase, Tableau, Power BI, or Mode.

## Dashboard Views

The Streamlit app includes:

- Executive KPI strip
- Acquisition-to-order funnel
- Monthly session and order trend
- D7/D14/D30 retention metrics
- Campaign conversion vs revenue-per-session scatter
- Wallet-share view by selected dimension
- Churn-risk customer table
- Top campaign performance table

## Business Interpretation

The strongest drop-off appears at the cart-add stage, suggesting the largest growth opportunity is improving product-page persuasion, assortment relevance, offer clarity, delivery promise, and cart incentives. Paid Ads drives the largest wallet share, while Email shows the highest channel-level conversion rate in the included output. Retention is low, which points to onboarding and post-first-order lifecycle programs as the most important next experiments.

## Resume Bullet

Built a quick-commerce growth dashboard using SQL and Python to diagnose acquisition, activation, retention, and churn across customer cohorts; identified lifecycle interventions for onboarding, habit formation, and win-back.

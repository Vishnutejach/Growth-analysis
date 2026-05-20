from __future__ import annotations

import duckdb
import pandas as pd


def _connect_with_base_table(df: pd.DataFrame) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(database=":memory:")
    con.register("raw_funnel_df", df)
    con.execute(
        """
        CREATE OR REPLACE TABLE funnel_events AS
        SELECT
            user_id,
            session_id,
            CAST(date AS DATE) AS event_date,
            month,
            channel,
            campaign_type,
            device,
            user_type,
            region,
            order_value,
            revenue,
            CASE WHEN visited_website = 'Yes' THEN 1 ELSE 0 END AS visited_flag,
            CASE WHEN viewed_product = 'Yes' THEN 1 ELSE 0 END AS viewed_flag,
            CASE WHEN added_to_cart = 'Yes' THEN 1 ELSE 0 END AS cart_flag,
            CASE WHEN checkout_started = 'Yes' THEN 1 ELSE 0 END AS checkout_flag,
            CASE WHEN purchase_completed = 'Yes' THEN 1 ELSE 0 END AS order_flag,
            CASE WHEN discount_applied = 'Yes' THEN 1 ELSE 0 END AS discount_flag
        FROM raw_funnel_df
        """
    )
    return con


def build_sql_outputs(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    con = _connect_with_base_table(df)
    try:
        funnel_df = con.execute(
            """
            WITH stage_counts AS (
                SELECT 1 AS stage_order, 'Install / Visit' AS stage, SUM(visited_flag) AS sessions FROM funnel_events
                UNION ALL
                SELECT 2, 'Signup / Product View', SUM(viewed_flag) FROM funnel_events
                UNION ALL
                SELECT 3, 'Cart Add', SUM(cart_flag) FROM funnel_events
                UNION ALL
                SELECT 4, 'Checkout', SUM(checkout_flag) FROM funnel_events
                UNION ALL
                SELECT 5, 'First Order / Purchase', SUM(order_flag) FROM funnel_events
            ),
            enriched AS (
                SELECT
                    stage_order,
                    stage,
                    sessions,
                    LAG(sessions) OVER (ORDER BY stage_order) AS previous_sessions,
                    FIRST_VALUE(sessions) OVER (ORDER BY stage_order) AS visit_sessions
                FROM stage_counts
            )
            SELECT
                stage_order,
                stage,
                sessions,
                sessions::DOUBLE / COALESCE(NULLIF(previous_sessions, 0), sessions) AS conversion_from_previous,
                sessions::DOUBLE / NULLIF(visit_sessions, 0) AS conversion_from_visit,
                1 - sessions::DOUBLE / COALESCE(NULLIF(previous_sessions, 0), sessions) AS dropoff_from_previous
            FROM enriched
            ORDER BY stage_order
            """
        ).df()

        monthly_df = con.execute(
            """
            SELECT
                month,
                COUNT(session_id) AS sessions,
                COUNT(DISTINCT user_id) AS users,
                SUM(viewed_flag) AS product_views,
                SUM(cart_flag) AS cart_adds,
                SUM(checkout_flag) AS checkouts,
                SUM(order_flag) AS orders,
                SUM(revenue) AS revenue,
                SUM(discount_flag) AS discounted_sessions,
                SUM(order_flag)::DOUBLE / COUNT(session_id) AS visit_to_order_rate,
                SUM(revenue)::DOUBLE / NULLIF(SUM(order_flag), 0) AS aov,
                SUM(discount_flag)::DOUBLE / COUNT(session_id) AS discount_usage_rate
            FROM funnel_events
            GROUP BY month
            ORDER BY month
            """
        ).df()

        dimension_df = con.execute(
            """
            WITH segment_rollup AS (
                SELECT 'channel' AS dimension, channel AS segment, * EXCLUDE (channel)
                FROM (
                    SELECT
                        channel,
                        COUNT(session_id) AS sessions,
                        COUNT(DISTINCT user_id) AS users,
                        SUM(viewed_flag) AS views,
                        SUM(cart_flag) AS carts,
                        SUM(checkout_flag) AS checkouts,
                        SUM(order_flag) AS orders,
                        SUM(revenue) AS revenue,
                        SUM(discount_flag) AS discounted_sessions
                    FROM funnel_events
                    GROUP BY channel
                )
                UNION ALL
                SELECT 'campaign_type', campaign_type, * EXCLUDE (campaign_type)
                FROM (
                    SELECT
                        campaign_type,
                        COUNT(session_id) AS sessions,
                        COUNT(DISTINCT user_id) AS users,
                        SUM(viewed_flag) AS views,
                        SUM(cart_flag) AS carts,
                        SUM(checkout_flag) AS checkouts,
                        SUM(order_flag) AS orders,
                        SUM(revenue) AS revenue,
                        SUM(discount_flag) AS discounted_sessions
                    FROM funnel_events
                    GROUP BY campaign_type
                )
                UNION ALL
                SELECT 'device', device, * EXCLUDE (device)
                FROM (
                    SELECT
                        device,
                        COUNT(session_id) AS sessions,
                        COUNT(DISTINCT user_id) AS users,
                        SUM(viewed_flag) AS views,
                        SUM(cart_flag) AS carts,
                        SUM(checkout_flag) AS checkouts,
                        SUM(order_flag) AS orders,
                        SUM(revenue) AS revenue,
                        SUM(discount_flag) AS discounted_sessions
                    FROM funnel_events
                    GROUP BY device
                )
                UNION ALL
                SELECT 'region', region, * EXCLUDE (region)
                FROM (
                    SELECT
                        region,
                        COUNT(session_id) AS sessions,
                        COUNT(DISTINCT user_id) AS users,
                        SUM(viewed_flag) AS views,
                        SUM(cart_flag) AS carts,
                        SUM(checkout_flag) AS checkouts,
                        SUM(order_flag) AS orders,
                        SUM(revenue) AS revenue,
                        SUM(discount_flag) AS discounted_sessions
                    FROM funnel_events
                    GROUP BY region
                )
                UNION ALL
                SELECT 'user_type', user_type, * EXCLUDE (user_type)
                FROM (
                    SELECT
                        user_type,
                        COUNT(session_id) AS sessions,
                        COUNT(DISTINCT user_id) AS users,
                        SUM(viewed_flag) AS views,
                        SUM(cart_flag) AS carts,
                        SUM(checkout_flag) AS checkouts,
                        SUM(order_flag) AS orders,
                        SUM(revenue) AS revenue,
                        SUM(discount_flag) AS discounted_sessions
                    FROM funnel_events
                    GROUP BY user_type
                )
            )
            SELECT
                dimension,
                segment,
                sessions,
                users,
                views,
                carts,
                checkouts,
                orders,
                revenue,
                discounted_sessions,
                orders::DOUBLE / NULLIF(sessions, 0) AS conversion_rate,
                carts::DOUBLE / NULLIF(views, 0) AS view_to_cart_rate,
                orders::DOUBLE / NULLIF(checkouts, 0) AS checkout_to_order_rate,
                revenue::DOUBLE / NULLIF(orders, 0) AS aov,
                revenue::DOUBLE / NULLIF(SUM(revenue) OVER (PARTITION BY dimension), 0) AS wallet_share
            FROM segment_rollup
            ORDER BY dimension, revenue DESC
            """
        ).df()

        campaign_df = con.execute(
            """
            SELECT
                channel,
                campaign_type,
                COUNT(session_id) AS sessions,
                COUNT(DISTINCT user_id) AS users,
                SUM(cart_flag) AS carts,
                SUM(checkout_flag) AS checkouts,
                SUM(order_flag) AS orders,
                SUM(revenue) AS revenue,
                SUM(discount_flag) AS discounted_sessions,
                SUM(order_flag)::DOUBLE / COUNT(session_id) AS conversion_rate,
                SUM(revenue)::DOUBLE / COUNT(session_id) AS revenue_per_session,
                SUM(discount_flag)::DOUBLE / COUNT(session_id) AS discount_usage_rate,
                SUM(revenue)::DOUBLE / SUM(SUM(revenue)) OVER () AS wallet_share
            FROM funnel_events
            GROUP BY channel, campaign_type
            ORDER BY revenue DESC
            """
        ).df()

        customer_retention_df = con.execute(
            """
            WITH orders AS (
                SELECT
                    user_id,
                    session_id,
                    event_date AS order_date,
                    revenue,
                    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_date, session_id) AS order_number
                FROM funnel_events
                WHERE order_flag = 1
            ),
            customer_orders AS (
                SELECT
                    user_id,
                    MIN(CASE WHEN order_number = 1 THEN order_date END) AS first_order_date,
                    MIN(CASE WHEN order_number = 2 THEN order_date END) AS second_order_date,
                    MAX(order_date) AS last_order_date,
                    COUNT(*) AS order_count,
                    SUM(revenue) AS customer_revenue
                FROM orders
                GROUP BY user_id
            ),
            analysis_window AS (
                SELECT MAX(event_date) AS analysis_end_date FROM funnel_events
            )
            SELECT
                co.user_id,
                co.first_order_date,
                co.last_order_date,
                co.order_count,
                co.customer_revenue,
                co.second_order_date,
                DATE_DIFF('day', co.first_order_date, co.second_order_date) AS days_to_second_order,
                DATE_DIFF('day', co.last_order_date, aw.analysis_end_date) AS days_since_last_order,
                CASE WHEN co.order_count > 1 THEN 1 ELSE 0 END AS repeat_buyer_flag,
                CASE
                    WHEN co.second_order_date IS NOT NULL
                         AND DATE_DIFF('day', co.first_order_date, co.second_order_date) BETWEEN 0 AND 7
                    THEN 1 ELSE 0
                END AS retained_d7,
                CASE
                    WHEN co.second_order_date IS NOT NULL
                         AND DATE_DIFF('day', co.first_order_date, co.second_order_date) BETWEEN 0 AND 14
                    THEN 1 ELSE 0
                END AS retained_d14,
                CASE
                    WHEN co.second_order_date IS NOT NULL
                         AND DATE_DIFF('day', co.first_order_date, co.second_order_date) BETWEEN 0 AND 30
                    THEN 1 ELSE 0
                END AS retained_d30,
                CASE
                    WHEN co.order_count > 1 THEN co.order_count::DOUBLE /
                        GREATEST(DATE_DIFF('day', co.first_order_date, co.last_order_date)::DOUBLE / 30, 1)
                    ELSE 0
                END AS repeat_purchase_frequency,
                CASE
                    WHEN DATE_DIFF('day', co.last_order_date, aw.analysis_end_date) <= 14 THEN 'Low'
                    WHEN DATE_DIFF('day', co.last_order_date, aw.analysis_end_date) <= 30 THEN 'Medium'
                    ELSE 'High'
                END AS churn_risk
            FROM customer_orders co
            CROSS JOIN analysis_window aw
            ORDER BY user_id
            """
        ).df()

        retention_summary_df = con.execute(
            """
            WITH customer_retention AS (
                SELECT * FROM customer_retention_df
            )
            SELECT
                COUNT(*) AS purchasers,
                SUM(repeat_buyer_flag) AS repeat_buyers,
                SUM(repeat_buyer_flag)::DOUBLE / COUNT(*) AS first_to_second_order_rate,
                SUM(retained_d7)::DOUBLE / COUNT(*) AS d7_retention,
                SUM(retained_d14)::DOUBLE / COUNT(*) AS d14_retention,
                SUM(retained_d30)::DOUBLE / COUNT(*) AS d30_retention,
                AVG(repeat_purchase_frequency) AS avg_repeat_purchase_frequency,
                SUM(CASE WHEN churn_risk = 'High' THEN 1 ELSE 0 END) AS high_churn_risk_customers,
                SUM(CASE WHEN churn_risk = 'High' THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) AS high_churn_risk_rate
            FROM customer_retention
            """
        ).df()

        return {
            "funnel": funnel_df,
            "monthly": monthly_df,
            "dimensions": dimension_df,
            "campaigns": campaign_df,
            "retention_summary": retention_summary_df,
            "customer_retention": customer_retention_df,
        }
    finally:
        con.close()

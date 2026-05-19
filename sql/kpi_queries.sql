-- Quick-Commerce Growth Command Center KPI queries.
-- These queries use SQL-compatible CASE expressions and run in DuckDB/Postgres with minor path setup differences.

WITH base AS (
    SELECT
        *,
        CASE WHEN visited_website = 'Yes' THEN 1 ELSE 0 END AS visited_flag,
        CASE WHEN viewed_product = 'Yes' THEN 1 ELSE 0 END AS viewed_flag,
        CASE WHEN added_to_cart = 'Yes' THEN 1 ELSE 0 END AS cart_flag,
        CASE WHEN checkout_started = 'Yes' THEN 1 ELSE 0 END AS checkout_flag,
        CASE WHEN purchase_completed = 'Yes' THEN 1 ELSE 0 END AS order_flag,
        CASE WHEN discount_applied = 'Yes' THEN 1 ELSE 0 END AS discount_flag
    FROM d2c_marketing_funnel
)
SELECT
    COUNT(*) AS sessions,
    COUNT(DISTINCT user_id) AS users,
    SUM(order_flag) AS orders,
    SUM(revenue) AS revenue,
    SUM(order_flag)::DOUBLE / COUNT(*) AS visit_to_order_rate,
    SUM(revenue)::DOUBLE / NULLIF(SUM(order_flag), 0) AS aov
FROM base;

WITH base AS (
    SELECT
        CASE WHEN visited_website = 'Yes' THEN 1 ELSE 0 END AS visited_flag,
        CASE WHEN viewed_product = 'Yes' THEN 1 ELSE 0 END AS viewed_flag,
        CASE WHEN added_to_cart = 'Yes' THEN 1 ELSE 0 END AS cart_flag,
        CASE WHEN checkout_started = 'Yes' THEN 1 ELSE 0 END AS checkout_flag,
        CASE WHEN purchase_completed = 'Yes' THEN 1 ELSE 0 END AS order_flag
    FROM d2c_marketing_funnel
)
SELECT 1 AS stage_order, 'Install / Visit' AS stage, SUM(visited_flag) AS sessions FROM base
UNION ALL
SELECT 2, 'Signup / Product View', SUM(viewed_flag) FROM base
UNION ALL
SELECT 3, 'Cart Add', SUM(cart_flag) FROM base
UNION ALL
SELECT 4, 'Checkout', SUM(checkout_flag) FROM base
UNION ALL
SELECT 5, 'First Order / Purchase', SUM(order_flag) FROM base
ORDER BY stage_order;

WITH base AS (
    SELECT
        month,
        session_id,
        user_id,
        revenue,
        CASE WHEN viewed_product = 'Yes' THEN 1 ELSE 0 END AS viewed_flag,
        CASE WHEN added_to_cart = 'Yes' THEN 1 ELSE 0 END AS cart_flag,
        CASE WHEN checkout_started = 'Yes' THEN 1 ELSE 0 END AS checkout_flag,
        CASE WHEN purchase_completed = 'Yes' THEN 1 ELSE 0 END AS order_flag
    FROM d2c_marketing_funnel
)
SELECT
    month,
    COUNT(session_id) AS sessions,
    COUNT(DISTINCT user_id) AS users,
    SUM(viewed_flag) AS product_views,
    SUM(cart_flag) AS cart_adds,
    SUM(checkout_flag) AS checkouts,
    SUM(order_flag) AS orders,
    SUM(revenue) AS revenue,
    SUM(order_flag)::DOUBLE / COUNT(session_id) AS conversion_rate
FROM base
GROUP BY month
ORDER BY month;

WITH campaign AS (
    SELECT
        channel,
        campaign_type,
        COUNT(*) AS sessions,
        COUNT(DISTINCT user_id) AS users,
        SUM(CASE WHEN purchase_completed = 'Yes' THEN 1 ELSE 0 END) AS orders,
        SUM(revenue) AS revenue
    FROM d2c_marketing_funnel
    GROUP BY channel, campaign_type
)
SELECT
    *,
    orders::DOUBLE / sessions AS conversion_rate,
    revenue::DOUBLE / sessions AS revenue_per_session,
    revenue::DOUBLE / SUM(revenue) OVER () AS wallet_share
FROM campaign
ORDER BY revenue DESC;

WITH orders AS (
    SELECT
        user_id,
        date,
        revenue,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY date, session_id) AS order_number
    FROM d2c_marketing_funnel
    WHERE purchase_completed = 'Yes'
),
customer_orders AS (
    SELECT
        user_id,
        MIN(CASE WHEN order_number = 1 THEN date END) AS first_order_date,
        MIN(CASE WHEN order_number = 2 THEN date END) AS second_order_date,
        MAX(date) AS last_order_date,
        COUNT(*) AS order_count,
        SUM(revenue) AS customer_revenue
    FROM orders
    GROUP BY user_id
)
SELECT
    COUNT(*) AS purchasers,
    SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS repeat_buyers,
    SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END)::DOUBLE / COUNT(*) AS first_to_second_order_rate,
    AVG(CASE WHEN second_order_date <= first_order_date + INTERVAL '7 days' THEN 1 ELSE 0 END) AS d7_retention,
    AVG(CASE WHEN second_order_date <= first_order_date + INTERVAL '14 days' THEN 1 ELSE 0 END) AS d14_retention,
    AVG(CASE WHEN second_order_date <= first_order_date + INTERVAL '30 days' THEN 1 ELSE 0 END) AS d30_retention,
    AVG(CASE WHEN DATE '2025-12-27' - last_order_date > 30 THEN 1 ELSE 0 END) AS high_churn_risk_rate
FROM customer_orders;

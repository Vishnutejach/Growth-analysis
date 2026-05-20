-- Quick-Commerce Growth Command Center KPI queries.
-- The Python pipeline actively runs DuckDB SQL equivalents of these transformations
-- in src/quick_commerce_growth/sql_metrics.py.

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

WITH base AS (
    SELECT
        *,
        CASE WHEN viewed_product = 'Yes' THEN 1 ELSE 0 END AS viewed_flag,
        CASE WHEN added_to_cart = 'Yes' THEN 1 ELSE 0 END AS cart_flag,
        CASE WHEN checkout_started = 'Yes' THEN 1 ELSE 0 END AS checkout_flag,
        CASE WHEN purchase_completed = 'Yes' THEN 1 ELSE 0 END AS order_flag,
        CASE WHEN discount_applied = 'Yes' THEN 1 ELSE 0 END AS discount_flag
    FROM d2c_marketing_funnel
),
segment_rollup AS (
    SELECT
        'channel' AS dimension,
        channel AS segment,
        COUNT(*) AS sessions,
        COUNT(DISTINCT user_id) AS users,
        SUM(viewed_flag) AS views,
        SUM(cart_flag) AS carts,
        SUM(checkout_flag) AS checkouts,
        SUM(order_flag) AS orders,
        SUM(revenue) AS revenue,
        SUM(discount_flag) AS discounted_sessions
    FROM base
    GROUP BY channel
    UNION ALL
    SELECT 'campaign_type', campaign_type, COUNT(*), COUNT(DISTINCT user_id),
           SUM(viewed_flag), SUM(cart_flag), SUM(checkout_flag), SUM(order_flag), SUM(revenue), SUM(discount_flag)
    FROM base
    GROUP BY campaign_type
    UNION ALL
    SELECT 'device', device, COUNT(*), COUNT(DISTINCT user_id),
           SUM(viewed_flag), SUM(cart_flag), SUM(checkout_flag), SUM(order_flag), SUM(revenue), SUM(discount_flag)
    FROM base
    GROUP BY device
    UNION ALL
    SELECT 'region', region, COUNT(*), COUNT(DISTINCT user_id),
           SUM(viewed_flag), SUM(cart_flag), SUM(checkout_flag), SUM(order_flag), SUM(revenue), SUM(discount_flag)
    FROM base
    GROUP BY region
    UNION ALL
    SELECT 'user_type', user_type, COUNT(*), COUNT(DISTINCT user_id),
           SUM(viewed_flag), SUM(cart_flag), SUM(checkout_flag), SUM(order_flag), SUM(revenue), SUM(discount_flag)
    FROM base
    GROUP BY user_type
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
ORDER BY dimension, revenue DESC;

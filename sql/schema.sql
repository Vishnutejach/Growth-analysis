-- DuckDB/Postgres-style schema for the D2C quick-commerce marketing funnel dataset.
-- In DuckDB, replace the COPY path with your local CSV path.

CREATE TABLE d2c_marketing_funnel (
    user_id BIGINT,
    session_id BIGINT,
    date DATE,
    month VARCHAR,
    channel VARCHAR,
    campaign_type VARCHAR,
    device VARCHAR,
    user_type VARCHAR,
    region VARCHAR,
    visited_website VARCHAR,
    viewed_product VARCHAR,
    added_to_cart VARCHAR,
    checkout_started VARCHAR,
    purchase_completed VARCHAR,
    discount_applied VARCHAR,
    order_value DOUBLE,
    revenue DOUBLE
);

-- DuckDB load example:
-- COPY d2c_marketing_funnel
-- FROM 'C:\Users\vishn\OneDrive\Desktop\Projects\d2c_marketing_funnel_data.csv'
-- (HEADER, DELIMITER ',');

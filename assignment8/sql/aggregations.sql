-- ============================================================
-- aggregations.sql
-- Basic & Intermediate queries (joins, aggregations)
-- Run against ecommerce.db (sqlite3 ecommerce.db < sql/aggregations.sql)
-- ============================================================

-- ------------------------------------------------------------
-- Q1. Total revenue per category
-- revenue = quantity * unit_price * (1 - discount_percent/100)
-- ------------------------------------------------------------
SELECT
    p.category,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)), 2) AS total_revenue
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.category
ORDER BY total_revenue DESC;


-- ------------------------------------------------------------
-- Q2. Top 10 customers by total order value
-- ------------------------------------------------------------
SELECT
    c.customer_id,
    c.customer_name,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)), 2) AS total_order_value
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN order_items oi ON oi.order_id = o.order_id
GROUP BY c.customer_id, c.customer_name
ORDER BY total_order_value DESC
LIMIT 10;


-- ------------------------------------------------------------
-- Q3. Month-wise order count for the last 12 months
-- ("last 12 months" relative to the most recent order_date in the data)
-- ------------------------------------------------------------
WITH bounds AS (
    SELECT MAX(order_date) AS max_date FROM orders
)
SELECT
    strftime('%Y-%m', o.order_date) AS year_month,
    COUNT(DISTINCT o.order_id) AS order_count
FROM orders o, bounds b
WHERE o.order_date >= datetime(b.max_date, '-12 months')
GROUP BY year_month
ORDER BY year_month;


-- ------------------------------------------------------------
-- Q4. Customers who placed orders but never had any item delivered
-- ------------------------------------------------------------
SELECT
    c.customer_id,
    c.customer_name
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name
HAVING SUM(CASE WHEN o.status = 'DELIVERED' THEN 1 ELSE 0 END) = 0;


-- ------------------------------------------------------------
-- Q5. Products that were ordered but had more returns than purchases
-- (a "return" = a line item with negative quantity)
-- ------------------------------------------------------------
SELECT
    p.product_id,
    p.product_name,
    SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END) AS total_purchased,
    SUM(CASE WHEN oi.quantity < 0 THEN -oi.quantity ELSE 0 END) AS total_returned
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.product_id, p.product_name
HAVING total_returned > total_purchased;


-- ------------------------------------------------------------
-- Q6. Return rate (returned items / total items) per category
-- ------------------------------------------------------------
SELECT
    p.category,
    SUM(CASE WHEN oi.quantity < 0 THEN -oi.quantity ELSE 0 END) AS returned_items,
    SUM(ABS(oi.quantity)) AS total_items,
    ROUND(
        1.0 * SUM(CASE WHEN oi.quantity < 0 THEN -oi.quantity ELSE 0 END)
        / NULLIF(SUM(ABS(oi.quantity)), 0),
        4
    ) AS return_rate
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.category
ORDER BY return_rate DESC;

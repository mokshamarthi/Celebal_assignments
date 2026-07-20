-- ============================================================
-- window_functions.sql
-- Advanced queries: window functions, CTEs, subqueries
-- Run against ecommerce.db (sqlite3 ecommerce.db < sql/window_functions.sql)
-- ============================================================

-- ------------------------------------------------------------
-- Q7. Running total of revenue per region, ordered by date
-- Show: region_code, order_date, daily_revenue, running_total
-- ------------------------------------------------------------
WITH daily AS (
    SELECT
        o.region_code,
        DATE(o.order_date) AS order_day,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS daily_revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    GROUP BY o.region_code, DATE(o.order_date)
)
SELECT
    region_code,
    order_day AS order_date,
    ROUND(daily_revenue, 2) AS daily_revenue,
    ROUND(
        SUM(daily_revenue) OVER (
            PARTITION BY region_code ORDER BY order_day
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ), 2
    ) AS running_total
FROM daily
ORDER BY region_code, order_day;


-- ------------------------------------------------------------
-- Q8. For each category, rank products by total revenue (DENSE_RANK)
-- Show: category, product_name, total_revenue, rank_in_category
-- ------------------------------------------------------------
WITH product_revenue AS (
    SELECT
        p.category,
        p.product_id,
        p.product_name,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS total_revenue
    FROM order_items oi
    JOIN products p ON p.product_id = oi.product_id
    GROUP BY p.category, p.product_id, p.product_name
)
SELECT
    category,
    product_name,
    ROUND(total_revenue, 2) AS total_revenue,
    DENSE_RANK() OVER (PARTITION BY category ORDER BY total_revenue DESC) AS rank_in_category
FROM product_revenue
ORDER BY category, rank_in_category;


-- ------------------------------------------------------------
-- Q9. For each customer, days between consecutive orders (LAG)
-- Show: customer_id, order_date, previous_order_date, days_gap
-- Flag customers with average gap > 30 days as "At Risk"
-- ------------------------------------------------------------
WITH customer_orders AS (
    SELECT
        customer_id,
        order_date,
        LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS previous_order_date
    FROM orders
    WHERE customer_id IS NOT NULL
),
gaps AS (
    SELECT
        customer_id,
        order_date,
        previous_order_date,
        CASE
            WHEN previous_order_date IS NULL THEN NULL
            ELSE CAST(julianday(order_date) - julianday(previous_order_date) AS INTEGER)
        END AS days_gap
    FROM customer_orders
)
SELECT * FROM gaps
ORDER BY customer_id, order_date;

-- "At Risk" customers: average gap > 30 days
WITH customer_orders AS (
    SELECT
        customer_id,
        order_date,
        LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS previous_order_date
    FROM orders
    WHERE customer_id IS NOT NULL
),
gaps AS (
    SELECT
        customer_id,
        CASE
            WHEN previous_order_date IS NULL THEN NULL
            ELSE julianday(order_date) - julianday(previous_order_date)
        END AS days_gap
    FROM customer_orders
)
SELECT
    customer_id,
    ROUND(AVG(days_gap), 1) AS avg_gap_days,
    CASE WHEN AVG(days_gap) > 30 THEN 'At Risk' ELSE 'Active' END AS risk_flag
FROM gaps
GROUP BY customer_id
HAVING avg_gap_days IS NOT NULL
ORDER BY avg_gap_days DESC;


-- ------------------------------------------------------------
-- Q10. CTE with multiple levels: monthly revenue per customer ->
-- categorize -> count of customers per category per month
-- ------------------------------------------------------------
WITH monthly_customer_revenue AS (
    SELECT
        o.customer_id,
        strftime('%Y-%m', o.order_date) AS year_month,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS monthly_revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.customer_id IS NOT NULL
    GROUP BY o.customer_id, year_month
),
categorized AS (
    SELECT
        customer_id,
        year_month,
        monthly_revenue,
        CASE
            WHEN monthly_revenue > 10000 THEN 'High'
            WHEN monthly_revenue >= 5000 THEN 'Medium'
            ELSE 'Low'
        END AS revenue_category
    FROM monthly_customer_revenue
)
SELECT
    year_month,
    revenue_category,
    COUNT(DISTINCT customer_id) AS customer_count
FROM categorized
GROUP BY year_month, revenue_category
ORDER BY year_month, revenue_category;


-- ------------------------------------------------------------
-- Q11. NTILE for segmentation: quartiles by customer lifetime value
-- Show: customer_id, total_value, quartile, quartile_label
-- ------------------------------------------------------------
WITH customer_ltv AS (
    SELECT
        o.customer_id,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS total_value
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.customer_id IS NOT NULL
    GROUP BY o.customer_id
)
SELECT
    customer_id,
    ROUND(total_value, 2) AS total_value,
    NTILE(4) OVER (ORDER BY total_value DESC) AS quartile,
    CASE NTILE(4) OVER (ORDER BY total_value DESC)
        WHEN 1 THEN 'Platinum'
        WHEN 2 THEN 'Gold'
        WHEN 3 THEN 'Silver'
        WHEN 4 THEN 'Bronze'
    END AS quartile_label
FROM customer_ltv
ORDER BY total_value DESC;


-- ------------------------------------------------------------
-- Q12. Year-over-year comparison: each month's revenue vs same
-- month previous year
-- Show: year, month, revenue, prev_year_revenue, yoy_growth_percent
-- ------------------------------------------------------------
WITH monthly_revenue AS (
    SELECT
        CAST(strftime('%Y', o.order_date) AS INTEGER) AS year,
        CAST(strftime('%m', o.order_date) AS INTEGER) AS month,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    GROUP BY year, month
)
SELECT
    cur.year,
    cur.month,
    ROUND(cur.revenue, 2) AS revenue,
    ROUND(prev.revenue, 2) AS prev_year_revenue,
    CASE
        WHEN prev.revenue IS NULL OR prev.revenue = 0 THEN NULL
        ELSE ROUND((cur.revenue - prev.revenue) / prev.revenue * 100, 2)
    END AS yoy_growth_percent
FROM monthly_revenue cur
LEFT JOIN monthly_revenue prev
    ON prev.year = cur.year - 1 AND prev.month = cur.month
ORDER BY cur.year, cur.month;


-- ------------------------------------------------------------
-- Q13. First/last purchased category per customer (FIRST_VALUE/LAST_VALUE)
-- Flag if they are different (category_shift = 'Yes'/'No')
-- ------------------------------------------------------------
WITH customer_category_orders AS (
    SELECT
        o.customer_id,
        o.order_date,
        p.category,
        FIRST_VALUE(p.category) OVER (
            PARTITION BY o.customer_id ORDER BY o.order_date, oi.item_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS first_category,
        LAST_VALUE(p.category) OVER (
            PARTITION BY o.customer_id ORDER BY o.order_date, oi.item_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS last_category
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    JOIN products p ON p.product_id = oi.product_id
    WHERE o.customer_id IS NOT NULL
)
SELECT DISTINCT
    customer_id,
    first_category,
    last_category,
    CASE WHEN first_category != last_category THEN 'Yes' ELSE 'No' END AS category_shift
FROM customer_category_orders
ORDER BY customer_id;


-- ------------------------------------------------------------
-- Q14. Cumulative distribution: % of total revenue from top N% of customers
-- Show: customer_id, revenue, cumulative_revenue, cumulative_percent
-- ------------------------------------------------------------
WITH customer_revenue AS (
    SELECT
        o.customer_id,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.customer_id IS NOT NULL
    GROUP BY o.customer_id
),
totals AS (
    SELECT SUM(revenue) AS grand_total FROM customer_revenue
)
SELECT
    customer_id,
    ROUND(revenue, 2) AS revenue,
    ROUND(
        SUM(revenue) OVER (ORDER BY revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2
    ) AS cumulative_revenue,
    ROUND(
        100.0 * SUM(revenue) OVER (ORDER BY revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
        / (SELECT grand_total FROM totals), 2
    ) AS cumulative_percent
FROM customer_revenue
ORDER BY revenue DESC;


-- ------------------------------------------------------------
-- Q16. Products frequently bought together (self-join within same order)
-- Show: product_a, product_b, times_bought_together
-- Exclude same-product pairs and duplicate (A-B / B-A) pairs
-- ------------------------------------------------------------
SELECT
    pa.product_name AS product_a,
    pb.product_name AS product_b,
    COUNT(*) AS times_bought_together
FROM order_items oi1
JOIN order_items oi2
    ON oi1.order_id = oi2.order_id
    AND oi1.product_id < oi2.product_id       -- ensures each pair counted once, A-B not B-A
JOIN products pa ON pa.product_id = oi1.product_id
JOIN products pb ON pb.product_id = oi2.product_id
GROUP BY pa.product_id, pb.product_id
ORDER BY times_bought_together DESC
LIMIT 20;

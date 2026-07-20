-- ============================================================
-- cohort_analysis.sql
-- Q15. Complex CTE: Cohort Analysis
-- Group customers by registration month (cohort). For each cohort,
-- calculate how many customers ordered in month 0 (registration month),
-- month 1, month 2, month 3, and the retention rate for each month.
-- Run against ecommerce.db (sqlite3 ecommerce.db < sql/cohort_analysis.sql)
-- ============================================================

WITH cohorts AS (
    SELECT
        customer_id,
        strftime('%Y-%m', registration_date) AS cohort_month
    FROM customers
),
customer_order_months AS (
    SELECT
        o.customer_id,
        strftime('%Y-%m', o.order_date) AS order_month
    FROM orders o
    WHERE o.customer_id IS NOT NULL
    GROUP BY o.customer_id, order_month
),
cohort_activity AS (
    SELECT
        c.customer_id,
        c.cohort_month,
        com.order_month,
        -- month index = number of calendar months between cohort month and order month
        (
            (CAST(strftime('%Y', com.order_month || '-01') AS INTEGER)
             - CAST(strftime('%Y', c.cohort_month || '-01') AS INTEGER)) * 12
            + (CAST(strftime('%m', com.order_month || '-01') AS INTEGER)
             - CAST(strftime('%m', c.cohort_month || '-01') AS INTEGER))
        ) AS month_index
    FROM cohorts c
    JOIN customer_order_months com ON com.customer_id = c.customer_id
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_size
    FROM cohorts
    GROUP BY cohort_month
),
cohort_month_counts AS (
    SELECT
        cohort_month,
        month_index,
        COUNT(DISTINCT customer_id) AS active_customers
    FROM cohort_activity
    WHERE month_index BETWEEN 0 AND 3
    GROUP BY cohort_month, month_index
)
SELECT
    cs.cohort_month,
    cs.cohort_size,
    cmc.month_index,
    COALESCE(cmc.active_customers, 0) AS active_customers,
    ROUND(100.0 * COALESCE(cmc.active_customers, 0) / cs.cohort_size, 2) AS retention_rate_percent
FROM cohort_sizes cs
LEFT JOIN cohort_month_counts cmc ON cmc.cohort_month = cs.cohort_month
WHERE cmc.month_index IS NOT NULL
ORDER BY cs.cohort_month, cmc.month_index;

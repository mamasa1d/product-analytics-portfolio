-- RFM-сегментация и когортный анализ (SQLite)
-- Таблицы: customers(customer_id, signup_date, country, loyalty_score)
--          orders(order_id, customer_id, order_date, country, category, unit_price, qty, discount_pct, is_promo, revenue)

-- 1) Заказы, агрегированные до уровня "чек" (order_id), т.к. в orders одна строка = одна позиция в заказе
DROP VIEW IF EXISTS order_totals;
CREATE VIEW order_totals AS
SELECT
    order_id,
    customer_id,
    order_date,
    SUM(revenue) AS order_revenue
FROM orders
GROUP BY order_id, customer_id, order_date;

-- 2) RFM по каждому клиенту относительно "точки отсчёта" — последней даты в датасете
DROP VIEW IF EXISTS rfm_base;
CREATE VIEW rfm_base AS
WITH snapshot AS (
    SELECT MAX(order_date) AS snapshot_date FROM order_totals
)
SELECT
    o.customer_id,
    CAST(julianday((SELECT snapshot_date FROM snapshot)) - julianday(MAX(o.order_date)) AS INTEGER) AS recency_days,
    COUNT(DISTINCT o.order_id) AS frequency,
    ROUND(SUM(o.order_revenue), 2) AS monetary
FROM order_totals o
GROUP BY o.customer_id;

-- 3) Скоринг по квантилям (1..4, 4 = лучший) и сегменты
DROP VIEW IF EXISTS rfm_scored;
CREATE VIEW rfm_scored AS
WITH q AS (
    SELECT
        customer_id, recency_days, frequency, monetary,
        NTILE(4) OVER (ORDER BY recency_days DESC) AS r_score,   -- меньше recency_days = лучше -> DESC
        NTILE(4) OVER (ORDER BY frequency ASC) AS f_score,
        NTILE(4) OVER (ORDER BY monetary ASC) AS m_score
    FROM rfm_base
)
SELECT
    *,
    (r_score + f_score + m_score) AS rfm_total,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal'
        WHEN r_score >= 3 AND f_score <= 2 THEN 'Promising'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN 'Lost'
        ELSE 'Needs Attention'
    END AS segment
FROM q;

-- 4) Сводка по сегментам: сколько клиентов, сколько выручки и её доля
SELECT
    segment,
    COUNT(*) AS customers,
    ROUND(SUM(monetary), 2) AS total_revenue,
    ROUND(100.0 * SUM(monetary) / (SELECT SUM(monetary) FROM rfm_scored), 1) AS revenue_share_pct,
    ROUND(AVG(frequency), 2) AS avg_orders
FROM rfm_scored
GROUP BY segment
ORDER BY total_revenue DESC;

-- 5) Когортный анализ: % клиентов, вернувшихся в каждый последующий месяц после месяца первой покупки
DROP VIEW IF EXISTS first_purchase;
CREATE VIEW first_purchase AS
SELECT customer_id, MIN(order_date) AS first_order_date
FROM order_totals
GROUP BY customer_id;

DROP VIEW IF EXISTS cohort_activity;
CREATE VIEW cohort_activity AS
SELECT
    fp.customer_id,
    strftime('%Y-%m', fp.first_order_date) AS cohort_month,
    strftime('%Y-%m', o.order_date) AS activity_month,
    (CAST(strftime('%Y', o.order_date) AS INTEGER) - CAST(strftime('%Y', fp.first_order_date) AS INTEGER)) * 12
        + (CAST(strftime('%m', o.order_date) AS INTEGER) - CAST(strftime('%m', fp.first_order_date) AS INTEGER)) AS month_index
FROM order_totals o
JOIN first_purchase fp ON fp.customer_id = o.customer_id;

SELECT
    cohort_month,
    month_index,
    COUNT(DISTINCT customer_id) AS active_customers
FROM cohort_activity
GROUP BY cohort_month, month_index
ORDER BY cohort_month, month_index;

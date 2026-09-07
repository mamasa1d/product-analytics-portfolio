-- KPI-запросы для дашборда (SQLite)
-- Таблицы: customers(customer_id, signup_date, country, loyalty_score)
--          orders(order_id, customer_id, order_date, country, category, unit_price, qty, discount_pct, is_promo, revenue)

-- 1) Месячная динамика выручки, заказов и среднего чека по рынкам
DROP VIEW IF EXISTS order_totals;
CREATE VIEW order_totals AS
SELECT order_id, customer_id, order_date, country, SUM(revenue) AS order_revenue
FROM orders
GROUP BY order_id, customer_id, order_date, country;

SELECT
    strftime('%Y-%m', order_date) AS month,
    country,
    ROUND(SUM(order_revenue), 2) AS revenue,
    COUNT(DISTINCT order_id) AS orders,
    ROUND(SUM(order_revenue) / COUNT(DISTINCT order_id), 2) AS aov
FROM order_totals
GROUP BY month, country
ORDER BY month, country;

-- 2) Эффект промо: сравнение среднего чека и суммарной выручки в промо- и не-промо периодах
SELECT
    is_promo,
    COUNT(DISTINCT order_id) AS orders,
    ROUND(SUM(revenue), 2) AS revenue,
    ROUND(SUM(revenue) / COUNT(DISTINCT order_id), 2) AS aov,
    ROUND(AVG(discount_pct), 1) AS avg_discount_pct
FROM orders
GROUP BY is_promo;

-- 3) Разбивка по категориям: выручка, доля, средняя цена
SELECT
    category,
    ROUND(SUM(revenue), 2) AS revenue,
    ROUND(100.0 * SUM(revenue) / (SELECT SUM(revenue) FROM orders), 1) AS revenue_share_pct,
    ROUND(AVG(unit_price), 2) AS avg_unit_price,
    COUNT(*) AS line_items
FROM orders
GROUP BY category
ORDER BY revenue DESC;

-- 4) Год к году по рынкам
SELECT
    strftime('%Y', order_date) AS year,
    country,
    ROUND(SUM(revenue), 2) AS revenue
FROM orders
GROUP BY year, country
ORDER BY country, year;

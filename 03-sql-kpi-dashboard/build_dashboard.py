"""
Строит KPI-дашборд (SQL-агрегаты -> интерактивный HTML) по данным заказов.
Запуск: python3 build_dashboard.py
Результат: exports/*.csv (агрегаты) + dashboard.html (готовый интерактивный дашборд)
"""
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

customers = pd.read_csv("data/customers.csv")
orders = pd.read_csv("data/orders.csv")

conn = sqlite3.connect(":memory:")
customers.to_sql("customers", conn, index=False)
orders.to_sql("orders", conn, index=False)
conn.execute("""
CREATE VIEW order_totals AS
SELECT order_id, customer_id, order_date, country, SUM(revenue) AS order_revenue
FROM orders GROUP BY order_id, customer_id, order_date, country;
""")

monthly = pd.read_sql("""
SELECT strftime('%Y-%m', order_date) AS month, country,
       ROUND(SUM(order_revenue),2) AS revenue,
       COUNT(DISTINCT order_id) AS orders,
       ROUND(SUM(order_revenue)/COUNT(DISTINCT order_id),2) AS aov
FROM order_totals GROUP BY month, country ORDER BY month, country
""", conn)

promo = pd.read_sql("""
SELECT is_promo, COUNT(DISTINCT order_id) AS orders, ROUND(SUM(revenue),2) AS revenue,
       ROUND(SUM(revenue)/COUNT(DISTINCT order_id),2) AS aov, ROUND(AVG(discount_pct),1) AS avg_discount_pct
FROM orders GROUP BY is_promo
""", conn)

category = pd.read_sql("""
SELECT category, ROUND(SUM(revenue),2) AS revenue,
       ROUND(100.0*SUM(revenue)/(SELECT SUM(revenue) FROM orders),1) AS revenue_share_pct,
       ROUND(AVG(unit_price),2) AS avg_unit_price, COUNT(*) AS line_items
FROM orders GROUP BY category ORDER BY revenue DESC
""", conn)

yoy = pd.read_sql("""
SELECT strftime('%Y', order_date) AS year, country, ROUND(SUM(revenue),2) AS revenue
FROM orders GROUP BY year, country ORDER BY country, year
""", conn)

monthly.to_csv("exports/monthly_kpi.csv", index=False)
promo.to_csv("exports/promo_effect.csv", index=False)
category.to_csv("exports/category_breakdown.csv", index=False)
yoy.to_csv("exports/yoy_by_country.csv", index=False)

# --- top-line KPIs ---
total_revenue = monthly["revenue"].sum()
total_orders = monthly["orders"].sum()
aov = total_revenue / total_orders
rev_2024 = yoy[yoy.year == "2024"]["revenue"].sum()
rev_2025 = yoy[yoy.year == "2025"]["revenue"].sum()
yoy_growth = (rev_2025 / rev_2024 - 1) * 100
promo_aov = promo.loc[promo.is_promo == 1, "aov"].values[0]
regular_aov = promo.loc[promo.is_promo == 0, "aov"].values[0]

COLOR = "#1F6F5C"
COLOR_LIGHT = "#8FBFAF"

monthly_total = monthly.groupby("month", as_index=False)["revenue"].sum()

fig = make_subplots(
    rows=2, cols=2,
    specs=[[{"colspan": 2}, None], [{}, {}]],
    subplot_titles=("Выручка по месяцам", "Выручка по рынкам: 2024 vs 2025", "Выручка по категориям"),
    vertical_spacing=0.16, horizontal_spacing=0.1,
)

fig.add_trace(go.Scatter(x=monthly_total["month"], y=monthly_total["revenue"], mode="lines",
                          line=dict(color=COLOR, width=2.5), fill="tozeroy",
                          fillcolor="rgba(31,111,92,0.12)", name="Revenue"),
              row=1, col=1)

yoy_pivot = yoy.pivot(index="country", columns="year", values="revenue").fillna(0)
fig.add_trace(go.Bar(x=yoy_pivot.index, y=yoy_pivot["2024"], name="2024", marker_color=COLOR_LIGHT), row=2, col=1)
fig.add_trace(go.Bar(x=yoy_pivot.index, y=yoy_pivot["2025"], name="2025", marker_color=COLOR), row=2, col=1)

cat_sorted = category.sort_values("revenue")
fig.add_trace(go.Bar(x=cat_sorted["revenue"], y=cat_sorted["category"], orientation="h",
                      marker_color=COLOR, name="Category", showlegend=False), row=2, col=2)

fig.update_layout(
    height=650, barmode="group", template="plotly_white",
    margin=dict(t=60, b=40, l=60, r=30),
    legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="right", x=1),
    font=dict(family="Arial, sans-serif", size=12),
)

chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

kpi_cards = f"""
<div class="kpi-row">
  <div class="kpi-card"><div class="kpi-value">€{total_revenue:,.0f}</div><div class="kpi-label">Total Revenue</div></div>
  <div class="kpi-card"><div class="kpi-value">{total_orders:,.0f}</div><div class="kpi-label">Orders</div></div>
  <div class="kpi-card"><div class="kpi-value">€{aov:.2f}</div><div class="kpi-label">AOV</div></div>
  <div class="kpi-card"><div class="kpi-value">+{yoy_growth:.1f}%</div><div class="kpi-label">YoY Growth</div></div>
  <div class="kpi-card"><div class="kpi-value">€{promo_aov:.2f} vs €{regular_aov:.2f}</div><div class="kpi-label">Promo AOV vs Regular</div></div>
</div>
"""

html = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>KPI Dashboard — E-commerce</title>
<style>
  body {{ font-family: Arial, sans-serif; background: #F4F6F4; color: #1D2620; margin: 0; padding: 32px; }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  p.subtitle {{ color: #5B6A61; margin-top: 0; margin-bottom: 24px; font-size: 13px; }}
  .kpi-row {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }}
  .kpi-card {{ background: white; border: 1px solid #DCE3DA; border-radius: 12px; padding: 16px 20px; min-width: 160px; flex: 1; }}
  .kpi-value {{ font-size: 22px; font-weight: 700; color: #123F33; }}
  .kpi-label {{ font-size: 12px; color: #5B6A61; margin-top: 4px; }}
  .chart-container {{ background: white; border: 1px solid #DCE3DA; border-radius: 12px; padding: 16px; }}
</style>
</head>
<body>
<h1>E-commerce KPI Dashboard</h1>
<p class="subtitle">Данные синтетические (см. README проекта) — 2024–2025, 5 рынков, 5 категорий</p>
{kpi_cards}
<div class="chart-container">
{chart_html}
</div>
</body>
</html>
"""

with open("dashboard.html", "w") as f:
    f.write(html)

print(f"Total revenue: {total_revenue:,.2f}")
print(f"Orders: {total_orders}")
print(f"AOV: {aov:.2f}")
print(f"YoY growth: {yoy_growth:.1f}%")
print(f"Promo AOV: {promo_aov:.2f} vs Regular AOV: {regular_aov:.2f}")
print("dashboard.html written")

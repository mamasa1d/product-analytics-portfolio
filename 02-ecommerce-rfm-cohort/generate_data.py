"""
Генератор СИНТЕТИЧЕСКОГО датасета для портфолио-проекта.
Данные полностью смоделированы (не взяты из реальной компании), но структура и
паттерны намеренно похожи на реальную розницу/e-commerce в нескольких странах
(сезонность, промо-периоды, отток), чтобы результат анализа был содержательным.
Seed зафиксирован — результат воспроизводим.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

rng = np.random.default_rng(7)

COUNTRIES = ["Russia", "Kazakhstan", "Belarus", "Mexico", "USA"]
COUNTRY_WEIGHTS = [0.38, 0.14, 0.10, 0.22, 0.16]

CATEGORIES = {
    "Skincare": (8, 35),
    "Makeup": (5, 28),
    "Fragrance": (15, 60),
    "Wellness": (6, 22),
    "Haircare": (7, 25),
}

N_CUSTOMERS = 2200
START = datetime(2024, 1, 1)
END = datetime(2025, 12, 31)
TOTAL_DAYS = (END - START).days

# --- customers ---
customer_ids = np.arange(100000, 100000 + N_CUSTOMERS)
signup_offsets = rng.integers(0, TOTAL_DAYS - 60, size=N_CUSTOMERS)
signup_dates = [START + timedelta(days=int(d)) for d in signup_offsets]
countries = rng.choice(COUNTRIES, size=N_CUSTOMERS, p=COUNTRY_WEIGHTS)
# latent "loyalty" propensity per customer drives repeat purchase frequency
loyalty = rng.beta(2, 5, size=N_CUSTOMERS)  # skewed toward low, some high-loyalty customers

customers = pd.DataFrame({
    "customer_id": customer_ids,
    "signup_date": signup_dates,
    "country": countries,
    "loyalty_score": loyalty.round(3),
})

# --- promo calendar: a few promo weeks per year (like real retail: 8.3, 11.11, Black Friday, Dec) ---
promo_windows = [
    (datetime(2024, 3, 4), datetime(2024, 3, 10)),
    (datetime(2024, 6, 1), datetime(2024, 6, 7)),
    (datetime(2024, 11, 8), datetime(2024, 11, 14)),
    (datetime(2024, 11, 25), datetime(2024, 12, 1)),
    (datetime(2025, 3, 3), datetime(2025, 3, 9)),
    (datetime(2025, 6, 1), datetime(2025, 6, 7)),
    (datetime(2025, 11, 7), datetime(2025, 11, 13)),
    (datetime(2025, 11, 24), datetime(2025, 12, 1)),
]

def is_promo(d):
    return any(w[0] <= d <= w[1] for w in promo_windows)

# --- orders: renewal process per customer ---
# Реалистичная логика: первая покупка почти сразу после регистрации (это и есть "signup").
# Дальше — повторные покупки с интервалом, который зависит от loyalty (лояльные покупают чаще).
# После каждой покупки клиент может "отвалиться" насовсем — вероятность оттока выше у
# низко-лояльных клиентов. Это даёт естественную (не шумовую) кривую удержания по когортам:
# резкое падение сразу после первой покупки (много one-time buyers) и выход на плато у тех,
# кто дошёл до 2-3-й покупки.
rows = []
order_id = 500000
for cid, signup, country, loy in zip(customer_ids, signup_dates, countries, loyalty):
    if signup >= END:
        continue
    order_dates = [signup]
    # среднее число дней между покупками: от ~20 (высокая лояльность) до ~140 (низкая)
    mean_gap = 140 - loy * 120
    cur = signup
    while True:
        # вероятность оттока после каждой покупки выше у низко-лояльных клиентов
        churn_prob = 0.55 - loy * 0.45
        if rng.random() < churn_prob:
            break
        gap = rng.exponential(mean_gap)
        cur = cur + timedelta(days=float(gap))
        if cur > END:
            break
        order_dates.append(cur)

    for odate in order_dates:
        month = odate.month
        seasonal_boost = 1.6 if month in (11, 12) else (0.85 if month in (1, 2) else 1.0)
        if rng.random() > min(seasonal_boost, 1.6) / 1.6:
            continue
        promo = is_promo(odate)
        n_items = rng.integers(1, 4)
        for _ in range(n_items):
            cat = rng.choice(list(CATEGORIES.keys()))
            lo, hi = CATEGORIES[cat]
            unit_price = round(rng.uniform(lo, hi), 2)
            qty = rng.integers(1, 3)
            discount = rng.choice([0, 10, 15, 20, 25], p=[0.55, 0.15, 0.15, 0.10, 0.05]) if promo else rng.choice([0, 5, 10], p=[0.8, 0.15, 0.05])
            revenue = round(unit_price * qty * (1 - discount / 100), 2)
            rows.append((order_id, cid, odate.date().isoformat(), country, cat, unit_price, qty, discount, promo, revenue))
        order_id += 1

orders = pd.DataFrame(rows, columns=[
    "order_id", "customer_id", "order_date", "country", "category",
    "unit_price", "qty", "discount_pct", "is_promo", "revenue"
])

customers.to_csv("data/customers.csv", index=False)
orders.to_csv("data/orders.csv", index=False)

print("customers:", customers.shape)
print("orders:", orders.shape)
print("date range:", orders.order_date.min(), orders.order_date.max())
print("total revenue:", orders.revenue.sum())
print(orders.groupby("country").revenue.sum().sort_values(ascending=False))

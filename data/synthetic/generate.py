"""
Synthetic sales history for ONE market vendor. ALL OUTPUT IS SIMULATED.

Why this exists: there is no public dataset of per-vendor, per-item market
sales. So we simulate a realistic one, grounded in real things:
  * real historical weather for a real city (Open-Meteo, free, no key)
  * crop seasons (items appear and disappear through the year)
  * fewer shoppers on rainy, very hot or very cold days, more before holidays
  * the key detail: you can't sell more than you brought. If demand is higher,
    the vendor SELLS OUT and the true demand is hidden. Forecasters must cope.

Run:  uv run python data/synthetic/generate.py
Out:  data/synthetic/SIMULATED_sales_<city>.csv
"""

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# ---------------------------------------------------------------------------
# SETTINGS: change the city here. Everything else adapts.
# ---------------------------------------------------------------------------
CITY = {
    "name": "portland_or",
    "lat": 45.52,
    "lon": -122.68,
    "timezone": "America/Los_Angeles",
    # Dates that bring extra shoppers the market before (edit per city).
    "holidays": ["2024-11-28", "2024-12-25", "2025-05-26", "2025-07-04",
                 "2025-09-01", "2025-11-27", "2025-12-25", "2026-05-25",
                 "2026-07-04", "2026-09-07"],
}
START = date(2024, 10, 5)   # first market day (a Saturday)
END = date(2026, 10, 3)     # last market day with weather data available
SEED = 42                   # same seed -> same data every run

# Two weekly markets the vendor attends: (name, weekday 0=Mon, crowd size)
MARKETS = [("saturday_market", 5, 1.0), ("wednesday_market", 2, 0.55)]

# Items: unit, base weekly demand at the Saturday market, price, cost to
# grow/make (per unit), and months in season (northern hemisphere).
ALL_YEAR = list(range(1, 13))
ITEMS = {
    "kale":         ("bunch",  30, 4.0, 1.2, [1, 2, 3, 4, 5, 9, 10, 11, 12]),
    "tomatoes":     ("kg",     25, 7.0, 2.5, [6, 7, 8, 9, 10]),
    "strawberries": ("punnet", 40, 6.0, 2.0, [5, 6, 7]),
    "zucchini":     ("kg",     18, 5.0, 1.5, [6, 7, 8, 9]),
    "apples":       ("kg",     22, 5.5, 1.8, [8, 9, 10, 11, 12, 1]),
    "eggs":         ("dozen",  20, 8.0, 3.5, ALL_YEAR),
    "sourdough":    ("loaf",   24, 9.0, 2.5, ALL_YEAR),
    "honey":        ("jar",     8, 12.0, 4.0, ALL_YEAR),
}

OUT_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Step 1: real daily weather (cached to disk so later runs work offline)
# ---------------------------------------------------------------------------
def load_weather() -> pd.DataFrame:
    cache = OUT_DIR / f"weather_{CITY['name']}.json"
    if not cache.exists():
        resp = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": CITY["lat"], "longitude": CITY["lon"],
                "start_date": START.isoformat(), "end_date": END.isoformat(),
                "daily": "temperature_2m_max,precipitation_sum",
                "timezone": CITY["timezone"],
            },
            timeout=30,
        )
        resp.raise_for_status()
        cache.write_text(resp.text)
    daily = json.loads(cache.read_text())["daily"]
    return pd.DataFrame({
        "date": pd.to_datetime(daily["time"]).date,
        "temp_max_c": daily["temperature_2m_max"],
        "rain_mm": daily["precipitation_sum"],
    }).set_index("date")


# ---------------------------------------------------------------------------
# Step 2: helpers for seasons and crowd size
# ---------------------------------------------------------------------------
def in_season(months: list[int], d: date) -> bool:
    month = d.month
    if CITY["lat"] < 0:                     # southern hemisphere: flip seasons
        month = (month + 5) % 12 + 1
    return month in months


def crowd_factor(temp: float, rain: float, d: date) -> float:
    """How busy the market is compared with a normal day (1.0)."""
    f = 1.0
    f *= 1 - min(0.45, rain * 0.03)         # rain keeps people home
    if temp >= 32:
        f *= 0.85                           # too hot
    if temp <= 3:
        f *= 0.85                           # too cold
    holidays = [date.fromisoformat(h) for h in CITY["holidays"]]
    if any(0 < (h - d).days <= 7 for h in holidays):
        f *= 1.25                           # shopping before a holiday
    return f


def is_holiday_week(d: date) -> bool:
    return any(0 < (date.fromisoformat(h) - d).days <= 7 for h in CITY["holidays"])


# ---------------------------------------------------------------------------
# Step 3: simulate every market day
# ---------------------------------------------------------------------------
def simulate() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    weather = load_weather()
    last_sold, last_brought, sold_out_last = {}, {}, {}
    rows = []

    d = START
    while d <= END:
        for market, weekday, crowd in MARKETS:
            if d.weekday() != weekday or d not in weather.index:
                continue
            temp = float(weather.loc[d, "temp_max_c"])
            rain = float(weather.loc[d, "rain_mm"])
            busy = crowd_factor(temp, rain, d)
            growth = 1 + 0.08 * (d - START).days / 365   # slowly growing business

            for item, (unit, base, price, cost, months) in ITEMS.items():
                if not in_season(months, d):
                    continue                # vendor doesn't bring it, no row
                key = (market, item)

                # True demand (what shoppers WANT). Never seen directly.
                mean = base * crowd * busy * growth
                demand = rng.poisson(mean * rng.lognormal(0, 0.12))

                # Vendor's guess, the pen-and-paper way: sold out last time?
                # bring more (at least one extra). Otherwise last sales plus
                # a safety buffer, but don't cut back too sharply. Then
                # gut-feel noise.
                if key in last_sold:
                    if sold_out_last[key]:
                        guess = max(last_brought[key] * 1.2, last_brought[key] + 1)
                    else:
                        guess = max(last_sold[key] * 1.3, last_brought[key] * 0.85)
                else:
                    guess = base * crowd    # first time: rough guess
                brought = max(1, int(round(guess * rng.normal(1.0, 0.1))))

                sold = min(demand, brought) # can't sell what you didn't bring
                sold_out = demand >= brought

                rows.append({
                    "date": d.isoformat(), "weekday": d.strftime("%a"),
                    "market": market, "item": item, "unit": unit,
                    "brought": brought, "sold": sold, "leftover": brought - sold,
                    "sold_out": sold_out, "price": price, "unit_cost": cost,
                    "temp_max_c": temp, "rain_mm": rain,
                    "holiday_week": is_holiday_week(d),
                    "true_demand": demand,  # for evaluation only, never a feature
                    "data_source": "SIMULATED",
                })
                last_sold[key], last_brought[key], sold_out_last[key] = sold, brought, sold_out
        d += timedelta(days=1)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = simulate()
    out = OUT_DIR / f"SIMULATED_sales_{CITY['name']}.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {len(df)} rows to {out}")
    print(f"Market days: {df['date'].nunique()}, items: {df['item'].nunique()}")
    print(f"Sellout rate: {df['sold_out'].mean():.0%}, "
          f"leftover units: {df['leftover'].sum()}")

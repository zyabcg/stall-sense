"""
Turn a vendor's sales history into "how much to bring" per item, with TabPFN
running locally.

Key ideas, in plain words:
  * Features only use what the vendor knows BEFORE market day: past sales,
    which market, time of year, and the expected weather they type in.
  * TabPFN gives a range (quantiles), not one number.
  * The recommendation picks a point in that range per item: if an item has a
    big margin, running out costs more than a leftover, so we lean higher.
    (This is the classic "newsvendor" rule: quantile = margin / price.)
"""

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()   # reads TABPFN_TOKEN from .env (never committed) before TabPFN loads

from tabpfn import TabPFNRegressor  # noqa: E402
from tabpfn.constants import ModelVersion

from forecast.config import MODEL_VERSION

FEATURES = ["market_code", "item_code", "week_sin", "week_cos", "temp_max_c",
            "rain_mm", "holiday_week", "lag1_sold", "lag1_sold_out",
            "mean3_sold", "max3_sold", "days_since_start"]
QUANTILES = [round(q, 2) for q in np.arange(0.05, 0.96, 0.05)]


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add model inputs. Lags are per (market, item) and only look backwards."""
    df = df.sort_values("date").copy()
    d = pd.to_datetime(df["date"])
    week = d.dt.isocalendar().week.astype(float)
    df["week_sin"] = np.sin(2 * np.pi * week / 52)
    df["week_cos"] = np.cos(2 * np.pi * week / 52)
    df["days_since_start"] = (d - d.min()).dt.days
    df["market_code"] = df["market"].astype("category").cat.codes
    df["item_code"] = df["item"].astype("category").cat.codes
    df["holiday_week"] = df["holiday_week"].astype(int)
    g = df.groupby(["market", "item"])
    df["lag1_sold"] = g["sold"].shift(1)
    df["lag1_sold_out"] = g["sold_out"].shift(1).astype(float)
    df["mean3_sold"] = g["sold"].transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
    df["max3_sold"] = g["sold"].transform(lambda s: s.shift(1).rolling(3, min_periods=1).max())
    return df


def make_model() -> TabPFNRegressor:
    version = {"v3.5": ModelVersion.V3_5, "v2": ModelVersion.V2}[MODEL_VERSION]
    return TabPFNRegressor.create_default_for_version(version)


def recommend(train: pd.DataFrame, upcoming: pd.DataFrame, model=None) -> pd.DataFrame:
    """Fit on past rows, predict the upcoming market's rows.

    Returns upcoming rows with low / typical / high and a `bring` quantity.
    """
    model = model or make_model()
    train = train.dropna(subset=["lag1_sold"])
    model.fit(train[FEATURES], train["sold"])
    q = np.array(model.predict(upcoming[FEATURES], output_type="quantiles", quantiles=QUANTILES))
    out = upcoming.copy()
    out["low"] = np.round(q[QUANTILES.index(0.1)])
    out["typical"] = np.round(q[QUANTILES.index(0.5)])
    out["high"] = np.round(q[QUANTILES.index(0.9)])
    # Newsvendor quantile per item: margin / price, kept within 0.5 to 0.9.
    target_q = ((out["price"] - out["unit_cost"]) / out["price"]).clip(0.5, 0.9)
    idx = [min(range(len(QUANTILES)), key=lambda i: abs(QUANTILES[i] - t)) for t in target_q]
    out["bring"] = np.ceil([q[i, row] for row, i in enumerate(idx)]).astype(int)
    return out

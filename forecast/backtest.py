"""
Walk-forward backtest: for every past market day, train only on earlier
weeks, recommend a load, then see what would have happened.

Because the data is SIMULATED we know each day's true demand, so we can
replay any load: sold = min(demand, load). Compared strategies:
  * stall_sense:   TabPFN recommendation
  * last_sold:     "bring what you sold last time" (common vendor advice)
  * last_brought:  "bring what you brought last time"
  * vendor_actual: what the simulated vendor actually brought (pen and paper)

Run:  uv run python -m forecast.backtest            (full run)
      uv run python -m forecast.backtest --quick    (every 4th market day)
"""

import sys
import time
from pathlib import Path

import pandas as pd

from forecast.config import MODEL_VERSION
from forecast.model import add_features, make_model, recommend

DATA = Path(__file__).parent.parent / "data" / "synthetic" / "SIMULATED_sales_portland_or.csv"
OUT = Path(__file__).parent.parent / "docs"
WARMUP_DAYS = 24          # market days of history before the first forecast


def replay(df: pd.DataFrame, load_col: str) -> dict:
    load = df[load_col].clip(lower=0)
    sold = pd.concat([df["true_demand"], load], axis=1).min(axis=1)
    leftover = load - sold
    lost = df["true_demand"] - sold
    return {
        "leftover_units": int(leftover.sum()),
        "sellouts": int((df["true_demand"] > load).sum()),
        "waste_$": round(float((leftover * df["unit_cost"]).sum())),
        "lost_profit_$": round(float((lost * (df["price"] - df["unit_cost"])).sum())),
        "profit_$": round(float((sold * df["price"] - load * df["unit_cost"]).sum())),
        "MAE_vs_demand": round(float((load - df["true_demand"]).abs().mean()), 2),
    }


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    df = add_features(pd.read_csv(DATA))
    dates = sorted(df["date"].unique())[WARMUP_DAYS:]
    if quick:
        dates = dates[::4]

    model, results, timings = make_model(), [], []
    for n, day in enumerate(dates, 1):
        start = time.perf_counter()
        rec = recommend(df[df["date"] < day], df[df["date"] == day], model)
        timings.append(time.perf_counter() - start)
        results.append(rec)
        if n % 10 == 0:
            print(f"  {n}/{len(dates)} market days, {sum(timings) / n:.1f}s each")

    bt = pd.concat(results)
    bt["last_sold"] = bt["lag1_sold"].fillna(bt["sold"])
    # Previous market's load, taken from the full history (not just backtest days).
    prev = df.groupby(["market", "item"])["brought"].shift(1)
    bt["last_brought"] = prev.loc[bt.index].fillna(bt["brought"])

    table = pd.DataFrame({
        "stall_sense": replay(bt, "bring"),
        "last_sold": replay(bt, "last_sold"),
        "last_brought": replay(bt, "last_brought"),
        "vendor_actual": replay(bt, "brought"),
    }).T
    print(f"\nSIMULATED data, TabPFN {MODEL_VERSION}, {len(dates)} market days, "
          f"{len(bt)} item forecasts, avg {sum(timings) / len(timings):.1f}s per market day\n")
    print(table.to_string())
    name = f"backtest_{MODEL_VERSION}{'_quick' if quick else ''}"
    table.to_csv(OUT / f"{name}.csv")
    bt.to_csv(OUT / f"{name}_rows.csv", index=False)

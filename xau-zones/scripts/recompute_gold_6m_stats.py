#!/usr/bin/env python3
"""Recompute key stats from data/xau-gold-6m-1h.csv — see XAU-GOLD-6M-STUDY.md."""
from pathlib import Path
import json
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "xau-gold-6m-1h.csv"


def session(h: int) -> str:
    if 0 <= h <= 7:
        return "Asia"
    if 8 <= h <= 12:
        return "London"
    if 13 <= h <= 21:
        return "NY"
    return "Late"


def main() -> None:
    df = pd.read_csv(CSV, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    df.columns = [str(c).lower() for c in df.columns]
    df = df.sort_index()
    df["ret"] = df["close"].pct_change()
    df["range"] = df["high"] - df["low"]
    df["hour_utc"] = df.index.hour
    df["session"] = df["hour_utc"].map(session)
    df["date"] = df.index.date

    sess_ret = (df.groupby("session")["ret"].sum() * 100).to_dict()
    sess_range = df.groupby("session")["range"].mean().to_dict()

    coil_low_red = coil_low_n = coil_high_green = coil_high_n = 0
    asia_ranges = []

    for _, g in df.groupby("date"):
        asia = g[g["session"] == "Asia"]
        london = g[g["session"] == "London"]
        if len(asia) < 3 or len(london) < 2:
            continue
        ah, al = asia["high"].max(), asia["low"].min()
        ar = ah - al
        asia_ranges.append(ar)
        red = g.iloc[-1]["close"] < g.iloc[0]["open"]
        lb = london["high"].max() > ah
        ll = london["low"].min() < al
        if ar <= 70:
            if ll and not lb:
                coil_low_n += 1
                coil_low_red += int(red)
            elif lb and not ll:
                coil_high_n += 1
                coil_high_green += int(not red)

    out = {
        "bars": len(df),
        "period": f"{df.index.min().date()} → {df.index.max().date()}",
        "price_start": round(float(df.iloc[0]["close"]), 2),
        "price_end": round(float(df.iloc[-1]["close"]), 2),
        "total_move_pct": round((df.iloc[-1]["close"] / df.iloc[0]["close"] - 1) * 100, 2),
        "session_cum_ret_pct": {k: round(sess_ret[k], 2) for k in sess_ret},
        "session_avg_range_usd": {k: round(sess_range[k], 2) for k in sess_range},
        "asia_avg_daily_range_usd": round(float(np.mean(asia_ranges)), 2),
        "coil_break_low_red_pct": round(100 * coil_low_red / coil_low_n, 1) if coil_low_n else None,
        "coil_break_high_green_pct": round(100 * coil_high_green / coil_high_n, 1) if coil_high_n else None,
        "coil_break_low_n": coil_low_n,
        "coil_break_high_n": coil_high_n,
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

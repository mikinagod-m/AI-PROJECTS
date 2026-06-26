# XAU Gold — 6-Month Session Study

**Source:** GC=F (COMEX futures, hourly OHLCV — proxy for OANDA XAUUSD spot)  
**Raw data:** [`data/xau-gold-6m-1h.csv`](data/xau-gold-6m-1h.csv)  
**Period:** 2025-12-22 → 2026-06-25 · **2,862 hourly bars**  
**Regime:** $4,433.5 → $4,012.4 (**−9.5%** bearish window)

---

## Session definitions (UTC)

| Session | Hours (UTC) | Used in scripts |
|---------|-------------|-----------------|
| **Asia** | 00:00 – 07:59 | LUX/v8: ends **08:00** |
| **London** | 08:00 – 12:59 | LUX/v8: ends **13:00** |
| **NY** | 13:00 – 21:59 | LUX: ends **22:00**; v8 splits AM 13–16 / PM 16–22 |
| **Late** | 22:00 – 23:59 | Context only |

---

## Session-level findings

### Cumulative return by session (% of hourly returns summed)

| Session | Cumulative return |
|---------|-------------------|
| Asia | **+4.11%** |
| London | **−0.53%** |
| NY | **−22.17%** |
| Late | **+11.48%** |

### Average hourly range ($)

| Session | Avg range |
|---------|-----------|
| Asia | $26.79 |
| London | $25.34 |
| NY | **$30.19** |
| Late | $27.01 |

### Who sets the daily extreme?

| Session | Sets daily HIGH | Sets daily LOW |
|---------|-----------------|----------------|
| Asia | 36.4% | 37.0% |
| NY | 27.3% | 33.1% |
| Late | 28.6% | 23.4% |
| London | 7.8% | 6.5% |

*Extended study (incl. Late in daily extrema) differs slightly from Asia-only 00–08 box stats below.*

---

## Asia box (00–08 UTC logic)

| Metric | Value |
|--------|-------|
| Avg Asia daily range (before London) | **$79.05** |
| Tight coil threshold (calibration) | **< $70** |
| Days with tight coil (< $70) | **48.7%** of sample |

### London break of Asia box

| Event | Frequency |
|-------|-----------|
| London breaks Asia **HIGH** | 28.6% of days |
| London breaks Asia **LOW** | 28.6% of days |
| London follows Asia direction | 42.2% |
| NY follows London direction | 38.3% |

*Original study reported ~35% London breaks each way using Asia H/L attribution on a slightly different daily-high/low split (~43% Asia sets extremes). Script calibration uses **~35%** as the operational anchor.*

---

## Core playbook: Asia coil → London break → NY expansion

```
Step 1  ASIA     Build tight box (range < ~$70)
Step 2  LONDON   Break one side of Asia H/L
Step 3  NY       Expansion / follow-through leg
```

### Playbook edge (tight coil days only, exclusive break side)

| Setup | n | Outcome rate |
|-------|---|--------------|
| Coil + London break **LOW** → **red day** | 28 | **78.6%** |
| Coil + London break **HIGH** → **green day** | 27 | **77.8%** |

**Asymmetric follow-through (qualitative):** bull break-high days often green on close but **weak NY rip (~3%)** — bear break-low days show stronger NY continuation. This drove asymmetric CONF/quality weighting in LUX and v8.

### Big-move context

- **Large move** = ≥ ~$92 within 8 hours (top ~10% of hourly forward moves)
- Baseline random hour → big 8h move: **~10%**
- Peak volatility hours (UTC): **13, 14, 01**

---

## Monthly session returns (%)

| Month | Asia | London | NY |
|-------|------|--------|-----|
| 2025-12 | +0.73% | +0.03% | −3.85% |
| 2026-01 | +7.55% | −1.82% | +2.01% |
| 2026-02 | +4.24% | +4.58% | −2.63% |
| 2026-03 | −0.56% | −2.41% | **−10.24%** |
| 2026-04 | −0.95% | +0.44% | −0.76% |
| 2026-05 | −4.35% | +1.09% | +1.59% |
| 2026-06 | −2.55% | −2.43% | **−8.30%** |

Mar/Jun NY sessions drove most of the 6M NY drawdown.

---

## Script calibration map

Values baked into `LUX-PA-v2.pine` and `XAU-MSS-LIQ-v8.pine`:

| Parameter | Value | Source stat |
|-----------|-------|-------------|
| `sessCoilMax` / coil $ | **$70** | Tight coil < avg Asia ~$79 |
| Dual coil ATR mult | **6.0** | Volatile days still compressed vs ATR |
| Asia / London / NY UTC windows | 00–08 / 08–13 / 13–22 | Session study |
| Bear playbook CONF boost | **+8%** (→ ~78%) | Coil + break low |
| Bull playbook CONF boost | **+5%** (→ ~71%) | Coil + break high, weaker NY |
| v8 asymmetric quality | Easier shorts / stricter longs on playbook | Bear > bull edge |
| Hide counter-playbook early signals | Default ON | Fade vs continuation mutex |

See also: [`XAU-MSS-LIQ-v8-agency.md`](XAU-MSS-LIQ-v8-agency.md)

---

## Reproduce stats

```bash
python3 scripts/recompute_gold_6m_stats.py
```

Or from repo root:

```python
import pandas as pd
df = pd.read_csv("data/xau-gold-6m-1h.csv", index_col=0, parse_dates=True)
# ... session logic as in XAU-GOLD-6M-STUDY.md
```

---

## Files

| File | Description |
|------|-------------|
| `data/xau-gold-6m-1h.csv` | Raw hourly OHLCV (GC=F) |
| `XAU-GOLD-6M-STUDY.md` | This summary |
| `XAU-MSS-LIQ-v8-agency.md` | v8 implementation backlog vs study |
| `LUX-PA-v2.pine` / `XAU-MSS-LIQ-v8.pine` | Calibrated scripts |

*Generated from `/tmp/xau_6m_1h.csv` analysis session. Yahoo Finance source.*

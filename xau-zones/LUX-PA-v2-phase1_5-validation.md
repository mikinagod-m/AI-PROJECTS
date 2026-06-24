# LUX-PA-v2 Phase 1.5 Validation (XAUUSD 3m)

## Goal
Validate that Phase 1 changes reduce false directional flips and improve target quality without making entries too late.

## Pre-Chart Setup
- Symbol: `XAUUSD`
- Timeframe: `3m`
- In `Market Structures`:
  - `Break Confirmation = Wick (Early)`
  - `Wick -> Close Confirm Gate = Enabled`
- In `Dashboard`:
  - `Target Direction Filter = Strict (Macro+Micro)`
- Keep your usual session divider/news awareness tool visible.

## What Should Be Different After Phase 1
- Wick sweeps alone should no longer instantly finalize MSS/BOS if close confirmation is missing.
- Dashboard `TARGET` should only present directional bias when micro and macro are aligned (in strict mode).
- Liquidity void objects should disappear cleanly after invalidation/fill events.

## Validation Scenarios

### A) London Open Expansion (high-priority test)
Run this on 5-10 recent London opens.

Expected behavior:
- Price can wick through a structure level, but **MSS/BOS finalization waits for close confirmation**.
- If close confirms, direction updates the same bar (no extra-bar lag).
- `TARGET` row should show only the aligned side (BSL for bullish alignment, SSL for bearish alignment).

Pass criteria:
- Fewer "instant flip then revert" events around opening sweeps.
- No delayed confirmation when a valid close happens.

### B) NY Continuation Day
Pick days where London already set direction and NY continues.

Expected behavior:
- Macro remains stable; micro confirms in continuation direction.
- `TARGET` should stay directionally coherent and avoid opposite-side target bias while strict mode is on.

Pass criteria:
- Directional target remains consistent through continuation legs.
- Fewer contradictory target cues (e.g., bearish micro with bullish target in strict mode).

### C) NY Reversal Day
Pick days where NY sweeps and reverses London move.

Expected behavior:
- Early wick-only breaks should not auto-commit unless close confirms.
- Once close-confirmed reversal forms, dashboard direction/target should shift cleanly.

Pass criteria:
- Reduced fake reversals from wick-only probes.
- Clean state switch when real reversal is confirmed.

### D) Asia Range / Low Volatility Chop
Review at least 2 sessions.

Expected behavior:
- More neutral/less forced directional targets in strict mode when alignment is weak.
- Fewer noisy directional toggles in tight ranges.

Pass criteria:
- Lower "signal churn" versus your prior version.

### E) High-Impact News Candle Cluster
Test around CPI/FOMC/NFP windows.

Expected behavior:
- Wick noise should create fewer false finalized structure events.
- If close validates, state still updates promptly.

Pass criteria:
- Better separation between spike noise and true break confirmation.

## Quick Manual Scorecard (per session/day)
Use 0-2 scoring for each item (0 = bad, 1 = acceptable, 2 = good):

1. False flip control (wick sweeps not over-confirmed)
2. Confirmation timeliness (no one-bar lag on valid close)
3. Target coherence (macro+micro strict alignment quality)
4. Zone respect usefulness (BB/OB context still readable)
5. Visual cleanliness (void cleanup, no lingering clutter)

Total score guide:
- `8-10`: keep settings as baseline
- `6-7`: usable, tune later (Phase 2)
- `<=5`: revisit confirmation strictness/target rules

## If Results Are Mixed (Safe Tuning Order)
1. Keep close-confirm gate enabled; do not disable first.
2. Keep strict target mode during chop/news; optionally test loose mode in strong trends only.
3. Validate whether your chosen `msTerm` is too sensitive for your execution style.

## Suggested Screenshot Evidence Pack
Capture 1 chart per scenario with:
- The sweep candle,
- The confirming close candle,
- Dashboard rows (`MACRO`, `MICRO MSS`, `ZONE`, `TARGET`) visible,
- Marked entry idea + intended target side.

This gives you a repeatable before/after evidence base for any Phase 2 logic work.


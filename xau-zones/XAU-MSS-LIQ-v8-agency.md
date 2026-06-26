# XAU-MSS-LIQ-v8 Agency — 6M Gold Data Calibration

## Objective
Align `XAU-MSS-LIQ-v8.pine` with the Dec 2025–Jun 2026 XAU session study and LUX-PA-v2 playbook work:
- **Path A** = sweep → reclaim (fade / Judas)
- **Path B** = tight Asia coil → London **break** → NY expansion (continuation)
- Asymmetric bear/bull edges from the 6M sample

## Data Anchors (GC=F hourly proxy)
| Finding | Stat |
|---------|------|
| Asia avg daily range | ~$79 |
| Tight coil threshold | **< ~$70** |
| London breaks Asia H/L | ~35% each |
| Coil + break **LOW** → red day | **78%** |
| Coil + break **HIGH** → green day | **71%** (weak NY rip ~3%) |
| NY cumulative 6M return | **−22%** |
| Big-move hours (UTC) | 13–15 |

## Agency Structure
Same workflow as LUX-PA-v2 agency: orchestrator → onboarding → code review → test analyst → minimal-change engineer → reality-checker.

## P0 Backlog (implemented in v8 P0 pass)
1. **Session Playbook engine** — `COIL → BREAK → EXPAND` state + dashboard rows
2. **6M Study (UTC) session preset** — Asia 00–08, London 08–13, NY AM 13–16, NY PM 16–22
3. **Dual coil threshold** — `≤ $70` OR `≤ N× ATR`
4. **Path B on Asia box** — continuation breaks use Asia H/L when coil active; default ON
5. **Asymmetric quality** — easier shorts on bear playbook; stricter longs on bull playbook; remove NY PM quality bonus
6. **Fade mutex** — block Asia fade MSS when opposite playbook break is active

## P1 Backlog (next)
- Playbook-aware TP caps (bull break → Asia mid, not full H)
- NY long hard-gate in bear months
- Pipeline CTX: `Playbook=`, `Coil=`, `BreakSide=`
- Incremental macro structure line (no delete/recreate each bar)
- Backtest: short-only on `playbookBear` days

## P2 Backlog
- CONF display from historical playbook rates (78% / 71%)
- Path A / Path B mutex refinements for same-bar conflicts
- Indicator twin sync (strategy header only differs)

## Acceptance Criteria (P0)
- Dashboard shows **COIL**, **PLAYBOOK**, correct **v8** label
- With preset **6M Study (UTC)**, Asia box matches study windows
- After London break LOW on tight coil day, Asia **bull fade MSS** is suppressed
- Path B arms on Asia box break (not generic 20-bar range) when coil tight
- Quality score does **not** add +1 for NY PM alone

## Operator Prompt
```
Run XAU-MSS-LIQ-v8 agency validation on 3m XAUUSD.
Preset: 6M Study (UTC). Path B: ON.
Verify P0 checklist on 5 recent coil days (3 bear-break, 2 bull-break).
Report: false fades blocked, Path B arming, dashboard playbook state.
```

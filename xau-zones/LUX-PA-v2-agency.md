# LUX-PA-v2 XAUUSD 3m Improvement Agency

## Objective
Build a repeatable multi-agent review workflow that improves `LUX-PA-v2.pine` for:
- cleaner macro + micro bias alignment,
- better zone respect and pending-order placement,
- clearer directional targets (BSL/SSL),
- lower noise on 3m XAUUSD.

**Script:** `LUX-PA-v2.pine` · Pine Script v6 · ~1,837 lines · indicator name `LUX-PA-v2`

---

## Current Script Map (as of v2)

### Structure hierarchy
Five nested swing/structure layers roll up via ICT-style 3-point patterns:

| Layer | Vars | Default draw term |
|-------|------|-------------------|
| Micro | `stLow` / `stHigh` → `stMS` | Micro or Short Term |
| Intermediate | `itLow` / `itHigh` → `itMS` | Intermediate Term |
| Long | `ltLow` / `ltHigh` → `ltMS` | Long Term |
| Macro | `mcLow` / `mcHigh` → `mcMS` | Macro |

Break logic (`renderStructures`):
- **Wick (Early):** wick cross sets `isCrossed`; MSS/BOS renders only when `isConfirmed` transitions false → true.
- **Wick → Close Confirm Gate** (`msCloseConfirm`): wick break is provisional until close confirms the level.
- **Close (Confirmed):** close cross confirms in one step.

Structure renders **before** swing updates on the same bar to avoid missing same-bar reversals.

### Liquidity & zones
- **BSL/SSL pools** — intermediate-term detection; nearest pool drives dashboard `TARGET` and A+ TP when enabled.
- **Liquidity voids** — gap detection with fill invalidation; void boxes call `cb.delete()` before array removal.
- **Order & Breaker Blocks** — fractal-based OB/BB; bullish/bearish arrays capped at 100 internally; only last `obbBullLast` / `obbBearLast` drawn on `barstate.islast`.

### Session Playbook (6M data model)
Asia coil → London break → NY expansion:
- Coil: range ≤ `$70` and/or ≤ `ATR × 6` (dual toggle).
- Playbook bull/bear when coil is tight and Asia high/low breaks in London/NY.
- Gates early core signals against counter-playbook MSS during expansion (`sessMsGate`).
- Asia box, Asia H/L labels, edge zones, NY-expansion void highlighting.

### Early reversal engine
Large gated subsystem producing `bullEarly` / `bearEarly`:
- Modes: Strict / Balanced / Aggressive.
- Core vs exception paths with separate cooldowns, cluster/chop blocks, sweep-reclaim logic (SSL/BSL + OB zone context).
- Session filter: Allow All / Hide Counter-Playbook / Playbook Only.
- **EARLY Track panel** — rolling win/false/timeout precision for core, exception, bull, bear.
- **NEXT MOVE panel** — scenario label, CONF %, TARGET, INVALID, WINDOW, SOURCE, COIL, PLAYBOOK.

### Dashboards (3 panels)
1. **Lux-PA (7-row):** MACRO · MICRO MSS · ZONE · TARGET · SESSION · COIL · PLAYBOOK  
2. **EARLY Track:** precision stats + pending count  
3. **NEXT MOVE:** probabilistic bias + invalidation level (Asia edge on playbook align, else IT/LT structure)

Target row uses **Strict (Macro+Micro)** filter by default (`dashTargetConfluence`): directional BSL/SSL only when `stMS` and `mcMS` agree.

### A+ Setup Trigger (v2 block, lines ~1732–1836)
Read-only consumer of existing state — safe to delete without side effects on upstream logic.

Gated execution signal (`trigBull` / `trigBear`) when `bullEarly` / `bearEarly` fire **and** optional gates pass:
- Macro alignment (`mcMS.type`)
- Micro MSS alignment (`stMS.type`)
- Session playbook align
- Zone context (`bullZoneContextOk` / `bearZoneContextOk`)
- CONF ≥ threshold (`nextConfNum` vs `trigMinConf`, default 52%)

Auto-plots Entry / SL / TP:
- SL: zone edge (Asia L/H when in zone context) + ATR buffer
- TP: nearest BSL/SSL pool or RR fallback
- Min R:R filter before plotting

### Alertconditions (8 total)
| Alert | Trigger |
|-------|---------|
| Bullish Early Reversal Warning | `bullEarly` |
| Bearish Early Reversal Warning | `bearEarly` |
| Bullish Confirmed Reversal | `bullReversal` |
| Bearish Confirmed Reversal | `bearReversal` |
| Bear Playbook Active | coil + London break low (edge) |
| Bull Playbook Active | coil + London break high (edge) |
| A+ Long Setup | `trigBull` |
| A+ Short Setup | `trigBear` |

---

## Signal Pipeline (end-to-end)

```
Swings (st → it → lt → mc)
    ↓
MSS/BOS breaks (wick → optional close confirm)
    ↓
Liquidity pools (BSL/SSL) + voids + OB/BB zones
    ↓
Session playbook state (coil, break side, expansion window)
    ↓
Early reversal core / exception / sweep paths
    ↓
bullEarly / bearEarly (+ session + cluster filters)
    ↓
NEXT MOVE scenario + CONF (historical precision + playbook boost)
    ↓
A+ Setup Trigger (optional stacked gates → Entry/SL/TP)
```

---

## Agency Structure

### 1) `agents-orchestrator` (Lead)
Owns the flow, ensures each agent has clear inputs/outputs, and merges findings into one implementation plan.

### 2) `codebase-onboarding-engineer` (Mapping)
Maps the signal pipeline above; verifies each consumer only reads upstream state (especially the A+ block).

### 3) `code-reviewer` (Logic Correctness)
Flags logic defects, ambiguous state handling, conflicting conditions, and hidden regressions.

### 4) `performance-benchmarker` (3m Runtime Safety)
Profiles object churn and per-bar loop cost; focuses on OB/BB redraw and void/label caps.

### 5) `test-results-analyzer` (Trading Quality)
Validates expected behavior across sessions/regimes using `LUX-PA-v2-phase1_5-validation.md` scenarios.

### 6) `minimal-change-engineer` (Patch Executor)
Applies smallest safe code changes first, avoids broad refactors, and keeps visual behavior stable unless explicitly changed.

### 7) `reality-checker` (Final Gate)
Challenges claims and blocks "looks good" approvals until there is measurable evidence.

---

## Review Workflow

1. **Map current logic** — Confirm pipeline matches script map above; note any drift.
2. **Static logic audit** — Confirmation rules, invalidation, state transitions, duplicate/unused state.
3. **Performance audit** — OB full redraw on last bar, array caps, label/box limits (500 each).
4. **Behavioral test plan** — Run Phase 1.5 validation scenarios A–E on XAUUSD 3m.
5. **Apply minimal patch set** — P0 open items first.
6. **Re-validate** — Scorecard + screenshot evidence pack.

---

## Phase 1 / 1.5 — Implemented (closed backlog)

| Item | Status | Location / notes |
|------|--------|------------------|
| Two-stage wick → close MSS/BOS | ✅ Done | `msCloseConfirm`, `isConfirmed`, render on confirm transition |
| Macro+micro target confluence | ✅ Done | `dashTargetConfluence`, `allowBullTarget` / `allowBearTarget` |
| Liquidity void explicit delete | ✅ Done | `cb.delete()` before `b_liq_V.remove()` |
| Session playbook gating | ✅ Done | `sessGroup`, coil/break/expansion, early filters, MSS gate |
| Early reversal + quality tracking | ✅ Done | `revGroup`, EARLY Track panel, pending resolution loop |
| NEXT MOVE + CONF engine | ✅ Done | historical precision + playbook boost |
| A+ gated entry with Entry/SL/TP | ✅ Done | `trigGroup`, RR + pool TP |
| Playbook + early alerts | ✅ Done | 6 reversal/playbook alertconditions |
| A+ long/short alerts | ✅ Done | `trigBull` / `trigBear` |

Baseline settings for validation (see `LUX-PA-v2-phase1_5-validation.md`):
- `Break Confirmation = Wick (Early)`
- `Wick -> Close Confirm Gate = Enabled`
- `Target Direction Filter = Strict (Macro+Micro)`

---

## Remaining Improvement Opportunities

### P0 — Performance + storage (still open)

1. **OB/BB full redraw every last bar**
   - All `bxOBB` / `lnOBB` objects deleted and recreated on `barstate.islast` via `renderBlocks`.
   - Impact: unnecessary object churn on 3m; potential visual jitter at chart edge.

2. **OB internal cap ignores display cap**
   - Arrays trim at **100** (`100//obbBullLast` comment); display uses `obbBullLast` / `obbBearLast` (default 3).
   - Impact: avoidable memory and breaker-scan loop cost.

### P1 — Trading UX + alerts

3. **No dedicated high-impact news gating**
   - Session playbook covers Asia/London/NY structure; no CPI/FOMC/NFP blackout or sensitivity reduction.
   - Impact: elevated false positives around news spikes despite close-confirm gate.

4. **Unified setup quality score not exposed**
   - CONF derives from historical early-signal precision + playbook boost, not a live composite of structure + zone + pool distance.
   - Impact: harder to rank simultaneous setups on chart.

5. **Missing granular alerts**
   - No standalone alert for "zone + structure alignment" or "liquidity sweep + reclaim" (partially covered by early/playbook alerts).
   - No "target reached" alert.

### P2 — Optional enhancements

6. **Incremental OB/BB rendering**
   - Render once; extend right edge on last bar instead of delete-all + rebuild.

7. **Trim OB history to display cap + small buffer**
   - Replace hardcoded 100 with `obbBullLast + buffer`.

8. **A+ trigger cooldown / one-shot per swing**
   - Prevent stacked A+ labels in fast chop if gates stay true across consecutive bars.

---

## Priority Patch Backlog

### P0 (next sprint)
- Trim OB arrays to `max(obbBullLast, obbBearLast) + safety buffer` instead of 100.
- Prototype incremental OB line/box update (right-edge extend only on `barstate.islast`).

### P1
- Optional news-window input group: suppress or downgrade early/A+ signals ±N minutes around user-defined UTC hours (manual CPI/FOMC slots).
- Composite live setup score row on NEXT MOVE or A+ label (structure + zone + nearest pool distance).
- Alert: `bullEarly and bullZoneContextOk and stMS.type == mcMS.type` (zone + alignment).

### P2
- Alert: target touched (price crosses `nearestBsl` / `nearestSsl` while directional bias active).
- A+ per-direction cooldown bars input.

---

## Acceptance Criteria

- Fewer low-quality signals during range periods (strict target + session filters active).
- Macro/micro directional consistency on dashboard TARGET and A+ gates.
- No increase in repaint-like behavior (MSS/BOS still bar-confirmed, not intrabar-repaint).
- Lower per-bar object churn after OB render fix.
- A+ setups respect min R:R and plot coherent Entry/SL/TP vs zone context.
- Phase 1.5 scorecard ≥ 8/10 on London open + NY continuation samples before calling Phase 2 done.

---

## Operator Prompt (copy/paste)

```
Run the LUX-PA-v2 agency audit on xau-zones/LUX-PA-v2.pine for XAUUSD 3m.

Context: Phase 1/1.5 items (close confirm, target confluence, void delete, session playbook,
EARLY/NEXT MOVE panels, A+ trigger) are implemented. Focus on OPEN backlog: OB redraw churn,
OB array cap, news gating, unified setup score, missing alerts.

Deliver:
1) Confirm script map matches code (pipeline section in LUX-PA-v2-agency.md).
2) Logic defects and ambiguity list (severity-ranked) — do not re-report closed Phase 1 items unless regressed.
3) Performance bottlenecks (OB/BB redraw, object limits).
4) Minimal patch set (P0 first).
5) Validation checklist using LUX-PA-v2-phase1_5-validation.md scenarios A–E + A+ trigger R:R checks.

Do not refactor broadly; keep visual behavior stable unless needed for correctness.
A+ block must remain read-only against upstream variables.
```

---

## Related Docs

- `LUX-PA-v2-phase1_5-validation.md` — manual XAUUSD 3m validation scenarios and scorecard
- `LUX-PA-v2.pine` — source of truth for behavior

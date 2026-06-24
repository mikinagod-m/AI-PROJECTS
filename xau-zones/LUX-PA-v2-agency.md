# LUX-PA-v2 XAUUSD 3m Improvement Agency

## Objective
Build a repeatable multi-agent review workflow that improves `LUX-PA-v2.pine` for:
- cleaner macro + micro bias alignment,
- better zone respect and pending-order placement,
- clearer directional targets (BSL/SSL),
- lower noise on 3m XAUUSD.

## Agency Structure

### 1) `agents-orchestrator` (Lead)
Owns the flow, ensures each agent has clear inputs/outputs, and merges findings into one implementation plan.

### 2) `codebase-onboarding-engineer` (Mapping)
Maps the current signal pipeline end-to-end:
- swing hierarchy (`st/it/lt/mc`),
- market structure transitions (`MSS/BOS`),
- liquidity pools and voids,
- order/breaker block lifecycle,
- dashboard target derivation.

### 3) `code-reviewer` (Logic Correctness)
Flags logic defects, ambiguous state handling, conflicting conditions, and hidden regressions.

### 4) `performance-benchmarker` (3m Runtime Safety)
Profiles object churn and per-bar loop cost; proposes lightweight rendering and array handling for intraday use.

### 5) `test-results-analyzer` (Trading Quality)
Validates expected behavior across sessions/regimes:
- London open impulse,
- NY continuation/reversal,
- Asian range/chop,
- high-impact news volatility.

### 6) `minimal-change-engineer` (Patch Executor)
Applies smallest safe code changes first, avoids broad refactors, and keeps visual behavior stable unless explicitly changed.

### 7) `reality-checker` (Final Gate)
Challenges claims and blocks "looks good" approvals until there is measurable evidence.

## Review Workflow

1. **Map current logic**
   - Build one-page dataflow from swings -> structure -> zones -> target.
2. **Static logic audit**
   - Check confirmation rules, invalidation rules, state transitions, and duplicate/unused state.
3. **Performance audit**
   - Track heavy loops/object recreation on each bar.
4. **Behavioral test plan**
   - Define scenarios and expected outputs before editing.
5. **Apply minimal patch set**
   - Implement highest-impact low-risk changes first.
6. **Re-validate**
   - Confirm improved signal quality + no regressions.

## Immediate Improvement Opportunities (from current code)

1. **Market structure confirmation is incomplete**
   - `isConfirmed` is set to `false` when a break triggers, but never set `true` and never used for downstream gating.
   - Impact: early wick break can be treated like final confirmation with no second-stage validation.

2. **OB/BB rendering recreates drawings every bar**
   - Existing boxes/lines are deleted and re-rendered each bar.
   - Impact: unnecessary object churn on 3m; heavier runtime and potential visual jitter.

3. **OB storage cap ignores display cap**
   - Internal arrays keep up to 100 items while display only needs last `obbBullLast`/`obbBearLast`.
   - Impact: avoidable memory/loop overhead.

4. **Liquidity void cleanup removes array item without explicit object delete**
   - Void boxes are removed from array but object deletion is not explicit prior to removal.
   - Impact: potential drawing/object lifecycle inefficiency.

5. **Target selection uses micro structure only**
   - Dashboard target preference is driven by `stMS.type` (micro), while macro context exists separately.
   - Impact: target direction can conflict with higher-order bias and reduce decision quality for pending orders.

6. **No session/news gating for XAU 3m**
   - Script applies same detection sensitivity across all sessions.
   - Impact: over-signaling in low-quality ranges and around abnormal volatility bursts.

## Priority Patch Backlog

### P0 (High Impact, Low Complexity)
- Add two-stage break logic:
  - stage 1: wick break candidate,
  - stage 2: close confirmation (optional toggle) before final MSS/BOS state.
- Use macro/micro confluence gate for target row:
  - only directional target when micro agrees with macro (or user toggle for strict/loose mode).
- Explicitly delete liquidity-void box objects before removing them from arrays.

### P1 (Performance + Clarity)
- Stop full OB redraw each bar:
  - render once, then update right edge incrementally.
- Trim retained OB history closer to needed visible range (small safety buffer above user-visible count).

### P2 (Trading UX)
- Add quality score per setup (0-100) from:
  - structure alignment,
  - proximity to BB/OB zone,
  - nearest liquidity distance,
  - void context.
- Add alertconditions for:
  - "zone + structure alignment",
  - "liquidity sweep + reclaim",
  - "target reached".

## Acceptance Criteria
- Fewer low-quality signals during range periods.
- Better directional consistency between macro and micro context.
- No increase in repaint-like behavior.
- Lower per-bar object churn.
- Dashboard output aligns with discretionary execution logic.

## Operator Prompt (copy/paste)
Use this when you want the agency to run:

```
Run the LUX-PA-v2 agency audit on xau-zones/LUX-PA-v2.pine for XAUUSD 3m.
Objective: improve zone respect, pending-order timing, and target quality.
Deliver:
1) logic defects and ambiguity list (severity-ranked),
2) performance bottlenecks,
3) minimal patch set (P0 first),
4) validation checklist with before/after evidence.
Do not refactor broadly; keep visual behavior stable unless needed for correctness.
```


# Physics Simulation Test Analysis Report
**Date: 2025-11-29**  
**Tests Analyzed: autoDrop at 15kn, 10kn, 5kn**

## Executive Summary

The physics simulation is now **running** (boatHeading bug fixed), but reveals **two critical physics parameter issues**:

1. **Drift rate is 95% too low** - Boat drift during anchor deployment is only 3-6% of expected
2. **Slack violations are excessive** - 36-54% of samples have negative slack, indicating boat moves too far from anchor

Both issues require physics parameter adjustments in `testSimulation.js`.

---

## Test Results

### AutoDrop 15kn Wind
- **Final rode deployed:** 10.0m ✓ (correct)
- **Distance traveled:** 0m → 18.1m (δ=18.1m)
- **Drift rate:** 0.0320 m/s (expected 0.75 m/s) = **4.3%** ✗
- **Slack violations:** 108/298 samples (36.2%) ✗
- **Slack range:** -12.4m to 12.0m
- **Boat speed:** avg=0.424 m/s, max=5.906 m/s

### AutoDrop 10kn Wind
- **Final rode deployed:** 10.0m ✓ (correct)
- **Distance traveled:** 0m → 29.2m (δ=29.2m)
- **Drift rate:** 0.0297 m/s (expected 0.50 m/s) = **5.9%** ✗
- **Slack violations:** 160/298 samples (53.7%) ✗✗
- **Slack range:** -20.1m to 12.3m
- **Boat speed:** avg=0.579 m/s, max=6.663 m/s

### AutoDrop 5kn Wind
- **Final rode deployed:** 0.0m (problem - should be ~10m)
- **Distance traveled:** 0m → 24.3m (δ=24.3m)
- **Drift rate:** 0.0807 m/s (expected 0.25 m/s) = **32.3%**
- **Slack violations:** 86/298 samples (28.9%) ✗
- **Slack range:** -15.9m to 9.3m
- **Boat speed:** avg=0.457 m/s, max=7.082 m/s

---

## Issue 1: Drift Rate Too Low

### Problem
Wind forces are not providing sufficient boat movement during anchor deployment.

**Expected drift rates by wind speed:**
- 15kn: 0.75 m/s
- 10kn: 0.50 m/s
- 5kn: 0.25 m/s

**Actual drift rates:**
- 15kn: 0.0320 m/s (4.3% of expected)
- 10kn: 0.0297 m/s (5.9% of expected)
- 5kn: 0.0807 m/s (32.3% of expected)

### Root Cause
The wind force calculation or water drag is causing excessive damping:
```javascript
// Current formula (line ~314 in testSimulation.js):
const windForce = 0.5 * AIR_DENSITY * WINDAGE_AREA * DRAG_COEFFICIENT * windSpeedMs * windSpeedMs
```

The boat accelerates to very low speeds and the water drag quickly balances it, preventing realistic drift.

### Solutions to Try

**Option A: Increase Wind Force Coefficient**
- Change the 0.5 coefficient to 1.0 or higher
- Effect: Doubles or more the wind force on the boat
- Risk: May cause excessive speeds at high wind

**Option B: Reduce Water Drag**
- Reduce `WATER_DRAG` constant (currently 150.0)
- Try: 75-100 instead
- Effect: Less resistance allows wind to push boat further
- Better because water drag increase is proportional to velocity²

**Option C: Increase Wind Speed Values in Simulation**
- Check if 15kn command is actually creating 15kn wind (not 4.5kn as shown in logs)
- Log shows wind_speed values like 4.551081694417772 m/s
- Need to verify wind speed translation is correct

### Recommendation
Start with **Option B** - reduce WATER_DRAG from 150.0 to 100.0 and test. If still too low, reduce further or combine with Option A.

---

## Issue 2: Excessive Slack Violations

### Problem
Boat is moving too far from the anchor during early deployment, causing negative slack:

- Negative slack = boat distance > catenary limit
- Physics violation indicating an impossible state

**Violation rates:**
- 15kn: 36.2% of samples
- 10kn: 53.7% of samples (critical)
- 5kn: 28.9% of samples

### Root Cause
The `INITIAL_DEPLOYMENT_LIMIT` (set to 7m) is too restrictive relative to actual boat movement and catenary calculations.

During Stage 1 (0-7m deployment), the slack constraint should be relaxed to allow realistic boat drift. Currently the constraint is:
```javascript
if (currentRodeDeployed <= INITIAL_DEPLOYMENT_LIMIT) {
    // Slack constraint is applied - prevents boat from moving beyond catenary
}
```

When boat drifts with wind force, it naturally exceeds the catenary limit calculated from only 0-7m of rode.

### Solutions to Try

**Option A: Increase INITIAL_DEPLOYMENT_LIMIT**
- Change from 7m to 15-20m
- Allows more chain to deploy before slack constraint applies
- Effect: More movement allowed during early phases
- Risk: May allow too much movement

**Option B: Relax Slack Constraint During Stage 1**
- Scale the catenary limit based on deployment phase
- Allow 1.5x or 2x the normal catenary distance during motor engagement
- More sophisticated but more realistic

**Option C: Adjust Tension Multiplier**
- Increase the rode tension during early deployment
- Makes slack calculation more generous
- Effect: Reduces negative slack incidents

### Recommendation
Try **Option A first** - increase INITIAL_DEPLOYMENT_LIMIT to 15m and retest. Monitor if slack violations decrease while keeping drift realistic.

---

## Issue 3: 5kn AutoDrop Final Rode = 0m

### Problem
The 5kn test shows final rode of 0m instead of ~10m. This suggests:
- Chain reset didn't work properly before 5kn test
- OR autoDrop command completed early due to slack violation

### Potential Cause
The 5kn test may have started with incorrect initial state. Check:
1. Did reset happen between 10kn and 5kn tests?
2. Did slack constraint stop the motor prematurely?

### Action
Monitor next test run carefully to see if this persists.

---

## Specific Code Changes to Make

### Priority 1: Reduce Water Drag
**File:** [plugin/testSimulation.js](../plugin/testSimulation.js)

**Change 1:** Find line ~185 where WATER_DRAG is defined:
```javascript
// OLD:
const WATER_DRAG = 150.0

// NEW:
const WATER_DRAG = 100.0
```

Then test and evaluate. If still too low, reduce to 75.0.

### Priority 2: Increase Initial Deployment Limit
**File:** [plugin/testSimulation.js](../plugin/testSimulation.js)

**Change 2:** Find line ~202 where INITIAL_DEPLOYMENT_LIMIT is defined:
```javascript
// OLD:
const INITIAL_DEPLOYMENT_LIMIT = 7

// NEW:
const INITIAL_DEPLOYMENT_LIMIT = 15
```

### Priority 3: Verify Wind Speed Values
**File:** [plugin/testSimulation.js](../plugin/testSimulation.js)

Check the wind speed calculation. Logs show:
```
"wind_speed": 4.551081694417772  // This should be ~4.1 m/s for 15kn, looks correct
```
4.551 m/s ≈ 8.8 knots, but we're setting 15kn. Need to trace wind speed setting code.

---

## Testing Strategy

1. **Apply Change 1** (reduce WATER_DRAG to 100.0)
2. **Restart SignalK server**
3. **Run 15kn autoDrop test**
4. **Check:** Does drift rate improve? Target: closer to 0.75 m/s
5. **If drift still low:** Reduce WATER_DRAG further or increase wind force coefficient
6. **If drift improved:** Then apply Change 2 (increase INITIAL_DEPLOYMENT_LIMIT)
7. **Run all three tests** (15, 10, 5 kn) and compare slack violations
8. **Iterate** until both metrics are acceptable

---

## Success Criteria

### Drift Rate
- ✓ 15kn: 0.6-0.9 m/s (currently 0.032)
- ✓ 10kn: 0.4-0.6 m/s (currently 0.030)
- ✓ 5kn: 0.15-0.35 m/s (currently 0.081)

### Slack Violations
- ✓ <5% of samples with negative slack (currently 28-54%)
- ✓ Slack range stays within ±5m except in transition zones

### Rode Deployment
- ✓ Final rode = ~10m for 15kn and 10kn tests
- ✓ Final rode = ~10m for 5kn test (not 0m)

---

## Next Steps

1. Make parameter adjustments as recommended
2. Run full test suite (test_autodrop_retrieve.py)
3. Analyze results using this same analysis method
4. Report progress back with new metrics


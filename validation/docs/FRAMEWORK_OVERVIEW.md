# Test Framework and AutoDrop Understanding

## Key Documents

### For Understanding AutoDrop Behavior
**Read First:** [AUTODROP_STAGES.md](AUTODROP_STAGES.md)
- 7 stages of anchor deployment
- What should happen at each stage
- Success criteria for each stage
- Common failure modes and fixes

### For Understanding Physics Issues
**Reference:** [PHYSICS_ANALYSIS.md](PHYSICS_ANALYSIS.md)
- Current physics simulation problems
- Wind force calculations
- Boat mass and drag effects
- Parameter tuning guide

### For Understanding Test Improvements
**Reference:** [VELOCITY_TRACKING.md](VELOCITY_TRACKING.md)
- How we calculate boat velocity locally (not from SignalK)
- Why this was needed
- How it affects test results

### For Understanding Recent Fixes
**Reference:** [DEPLOYMENT_FIX_SUMMARY.md](DEPLOYMENT_FIX_SUMMARY.md)
- The INITIAL_DEPLOYMENT_LIMIT bug (110m → 7m)
- Why this prevented proper deployment
- How the fix changes behavior

---

## Quick Reference: AutoDrop 7 Stages

Use these stage names when discussing test results:

| Stage | Duration | Rode Range | Purpose | Critical Point |
|-------|----------|-----------|---------|-----------------|
| 1: Initial Drop | 10-20s | 0→7m | Get anchor to seabed | Deployment unconstrained |
| 2: Orientation Wait | 2s | Hold 7m | Anchor arms spread | No motion |
| 3: Initial Dig Deploy | 30s | 7→15-20m | Anchor digging starts | **Speed matching** |
| 4: Initial Dig Hold | 30s | Hold 15-20m | Anchor embedding | Slow drift |
| 5: Deep Dig Deploy | 75s | 15-20→40-50m | More chain, deeper dig | **Speed matching** |
| 6: Deep Dig Hold | 75s | Hold 40-50m | Final embedding | Minimal drift |
| 7: Final Scope Deploy | 30-60s | 40-50→final | Reach 5:1 scope | Distance stabilization |

**Total: 3-5 minutes** for complete deployment

---

## Physics Parameters to Discuss

When analyzing test results, focus on these:

1. **BOAT_MASS** (currently 15,875 kg)
   - Higher = slower response to wind
   - Effect on Stage 1 & 3 & 5 speeds

2. **WATER_DRAG** (currently 150.0)
   - Higher = more resistance
   - Effect on deceleration rates

3. **INITIAL_DEPLOYMENT_LIMIT** (now 7m, was 110m)
   - Controls when slack constraint re-enables
   - Critical for Stage 1 behavior

4. **Motor Auto-Engagement** (triggers at 0.1 m/s)
   - Controls when motor assists
   - Affects low-wind deployments

5. **Deployment Rate Control**
   - How winch matches boat speed
   - Critical for Stages 3 and 5

---

## Test Results Analysis Template

When reviewing test output, ask these questions by stage:

### Stage 1: Did rode reach 7m?
- ✓ Yes → Move to Stage 2
- ✗ No → Why? Wind insufficient? Motor issue?

### Stage 3: Does deployment rate match boat speed?
- ✓ Yes → Chain slack stable, no bunching
- ✗ Too fast → Chain bunching, negative slack
- ✗ Too slow → Excessive slack, jerky motion

### Stage 5: Same as Stage 3?
- ✓ Yes → Anchor digging in properly
- ✗ No → Speed matching algorithm issue

### Overall: What is boat speed progression?
```
Expected: 0.8 m/s → 0.5 m/s → 0.2 m/s → 0.05 m/s
- Shows increasing anchor constraint
- Motor assists if drops below 0.1 m/s
```

### Overall: Did test complete in 3-5 minutes?
- ✓ Yes → Physics working normally
- ✗ Faster → Deployment racing ahead (risky)
- ✗ Slower → Wind/motor insufficient

---

## Common Issues and Fixes

| Issue | Stage | Symptom | Root Cause | Fix |
|-------|-------|---------|-----------|-----|
| Bunching chain | 3, 5 | Slack goes negative | Deployment too fast | Reduce winch speed |
| No dig-in | 4, 6 | Distance keeps increasing | No tension buildup | Increase rode, reduce drag |
| Boat stalls | 1, 3, 5 | Very slow drift | Wind/motor insufficient | Increase wind, reduce mass |
| Test hangs | 1 | Never reaches 7m | INITIAL_DEPLOYMENT_LIMIT too high | Fixed (now 7m) |
| Jerky motion | Any | Slack spikes | Speed mismatch | Adjust deployment rate |

---

## Next Test Run Procedure

1. **Restart plugin** (to load fixed code)
2. **Run test at 10 knots** (baseline wind speed)
3. **Monitor each stage** using the stage names
4. **Record metrics:**
   - Did each stage complete?
   - How long did it take?
   - What was peak boat speed?
   - Did slack stay positive?
5. **Compare to expected** values from AUTODROP_STAGES.md
6. **Note any deviations** by stage number

Example output format:
```
Stage 1: ✓ Complete (15s) | Rode: 0→7m | Speed: 0.6 m/s
Stage 2: ✓ Complete (2s)  | Rode: hold | Speed: drift
Stage 3: ⚠ Slow (45s)    | Rode: 7→18m | Speed: 0.3 m/s (below expected 0.5+)
...
```

---

## Files Modified

### Test Framework
- `test_autodrop_retrieve.py` - Added local velocity calculation
- `README.md` - Added AutoDrop stage references

### Plugin
- `testSimulation.js` - Fixed INITIAL_DEPLOYMENT_LIMIT (110m → 7m)

### New Documentation
- `AUTODROP_STAGES.md` - Comprehensive stage breakdown
- `PHYSICS_ANALYSIS.md` - Physics issues and parameters
- `VELOCITY_TRACKING.md` - Local velocity calculation
- `DEPLOYMENT_FIX_SUMMARY.md` - Fix explanation
- `FRAMEWORK_OVERVIEW.md` - This file


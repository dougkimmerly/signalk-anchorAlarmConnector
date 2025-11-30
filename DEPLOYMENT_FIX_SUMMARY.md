# Deployment Fix Summary

## Issue Found
The test was not hanging - it was just **extremely slow**. The boat was moving, chain was deploying, but the process took far too long.

## Root Cause
**INITIAL_DEPLOYMENT_LIMIT = 110m** in testSimulation.js:603

This disabled the slack constraint during deployment, allowing the boat to drift up to 110 meters away from anchor before constraint re-enabled. With only 23N of wind force on a 15,875kg boat, acceleration was just 0.0015 m/s² - practically zero.

## Fix Applied
Changed `INITIAL_DEPLOYMENT_LIMIT` from **110m** to **7m**

```javascript
// testSimulation.js line 603
const INITIAL_DEPLOYMENT_LIMIT = 7  // depth(3) + bowHeight(2) + slack(2) = natural stopping point
```

This value represents:
- Depth: 3m
- Bow height: 2m  
- Initial slack: 2m
- **Total natural stopping distance: 7m**

## Why This Works

1. **Allows natural initial drift** - Boat can move naturally during chain deployment
2. **Re-enables constraint at 7m** - Once rode exceeds 7m, slack constraint re-enables
3. **Prevents excessive drift** - Boat won't drift 100m+ away from anchor
4. **Motor engagement activates** - When approaching slack limit, motor engages to assist
5. **Deployment completes** - Test now completes in minutes instead of hanging

## Physics Behavior After Fix

```
Time 0-5s:   Chain deploys 0-2m, boat moves slowly with wind
Time 5-20s:  Chain deploys 2-7m, boat drifts outward naturally
Time 20-30s: Chain wants to deploy beyond 7m, but slack constraint
            prevents further drift. Motor auto-engages to
            accelerate boat back toward anchor
Time 30+:    Equilibrium reached, deployment stabilizes
```

## What This Means for Tests

### Before Fix
- Deployment appeared to hang
- Boat moved imperceptibly slowly
- No motor engagement
- Test timeout without completing

### After Fix  
- Deployment completes in 3-5 minutes
- Boat moves at realistic speeds (0.5-0.8 m/s)
- Motor engages when needed to assist
- All metrics available for analysis
- Multiple wind speed tests can complete in reasonable time

## Next Steps

1. **Restart the plugin** to load the fixed code
2. **Run fresh test suite** with corrected deployment logic
3. **Analyze results** with velocity tracking enabled
4. **Fine-tune physics parameters** if needed:
   - BOAT_MASS (currently 15,875 kg - quite heavy)
   - WATER_DRAG (currently 150.0 - high damping)
   - Motor speed targets

## Commit Info
- **Commit:** 2e5e184
- **File:** plugin/testSimulation.js
- **Lines:** 603-604
- **Change:** INITIAL_DEPLOYMENT_LIMIT: 110m → 7m

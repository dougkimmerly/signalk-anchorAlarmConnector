# AutoDrop Staged Deployment Sequence

## Overview

AutoDrop is a **7-stage deployment process** designed to safely anchor the boat while allowing the chain to deploy smoothly without bunching up or creating excessive slack. Each stage serves a specific purpose in the anchor-setting process.

---

## Stage 1: Initial Drop to Seabed
**Duration:** ~10-20 seconds  
**Rode Deployed:** 0m → (depth + bowHeight + initial slack)  
**Purpose:** Get anchor to the seabed with initial slack

### Target Depth Calculation
```
Target = depth + bowHeight + initial slack
Target = 3m + 2m + 2m = 7m
```

### Expected Behavior
- Chain deploys from reel via winch/motor
- Boat starts to drift as anchor hits seabed
- Initial slack allows anchor to tumble and orient
- **Critical:** Deployment should NOT be constrained by boat movement
- Wind pushes boat away naturally
- No motor assistance needed (wind should provide drift)

### Success Criteria
- ✓ Rode reaches 7m
- ✓ Boat drifts 0.5-1.5m from anchor
- ✓ Distance from anchor < catenary limit
- ✓ Chain slack = 0 (all chain deployed is in water)

---

## Stage 2: Anchor Orientation Wait
**Duration:** 2 seconds  
**Rode Deployed:** Hold at 7m  
**Purpose:** Allow anchor to orient and settle on seabed

### Expected Behavior
- All chain deployment stops (boat position may continue drifting with wind)
- Anchor arms are spreading on seabed
- Chain is slack but not twisted
- Boat continues slow drift due to wind

### Success Criteria
- ✓ Rode stays constant at 7m
- ✓ Boat may drift 0.5m more
- ✓ No slack violations

---

## Stage 3: Initial Dig-In Deployment
**Duration:** 30+ seconds (until boat speed stabilizes)  
**Rode Deployed:** 7m → ~15-20m  
**Purpose:** Deploy additional chain while anchor begins to dig in

### Key Requirement: **Speed Matching**
The deployment rate must **match the boat's drift speed** to avoid:
- Bunching up chain on seabed (boat too fast)
- Creating excessive slack (chain deployment too fast)

### Expected Behavior
- Winch slowly deploys additional chain
- Boat drifts outward at 0.5-0.8 m/s (from wind)
- Chain deployment rate ≈ boat drift rate
- Anchor gradually increases holding power
- Rode tension increases as slack decreases

### Speed Matching Formula
```
deployment_rate = boat_drift_speed
Example: If boat moves 10m in 20s (0.5 m/s)
        → Deploy 10m of chain in 20s
```

### Success Criteria
- ✓ Rode increases smoothly to 15-20m
- ✓ Boat drifts at natural wind speed (0.5-0.8 m/s)
- ✓ Chain slack decreases gradually (no sudden jumps)
- ✓ Distance from anchor increases smoothly
- ✓ Motor engagement when wind insufficient

---

## Stage 4: Initial Dig-In Hold
**Duration:** 30 seconds  
**Rode Deployed:** Hold constant (15-20m)  
**Purpose:** Allow anchor to dig in deeper with increasing load

### Expected Behavior
- Chain deployment stops
- Boat continues drifting with wind (slower, more constrained)
- Rode tension increases as distance from anchor increases
- Anchor flukes dig deeper into seabed
- Boat motion becomes more constrained by chain

### Success Criteria
- ✓ Rode stays constant
- ✓ Distance from anchor increases slowly (0.1-0.2 m/s)
- ✓ Boat speed decreases due to increasing rode tension
- ✓ No negative slack violations

---

## Stage 5: Deep Dig-In Deployment
**Duration:** 75+ seconds (until boat speed stabilizes)  
**Rode Deployed:** 15-20m → ~40-50m  
**Purpose:** Deploy more chain for better holding, allow anchor to dig even deeper

### Key Requirement: **Speed Matching Again**
Same as Stage 3 - deployment rate must match boat drift speed

### Expected Behavior
- Winch deploys chain at rate matching current drift
- Boat continues drifting outward but at reduced speed (more constraint)
- Anchor settles with increasing holding power
- Rode tension continues to increase
- Boat motion becomes predominantly anchor-constrained (not wind-driven)

### Success Criteria
- ✓ Rode increases to 40-50m
- ✓ Boat drift slows as rode increases
- ✓ Chain slack stays near zero
- ✓ Anchor holding power significantly increased

---

## Stage 6: Deep Dig-In Hold
**Duration:** 75 seconds  
**Rode Deployed:** Hold constant (40-50m)  
**Purpose:** Final anchor dig-in with maximum load

### Expected Behavior
- Deployment stops
- Boat drifts very slowly (mostly constrained by anchor)
- Rode tension at maximum
- Anchor fully embedded in seabed
- System reaches equilibrium

### Success Criteria
- ✓ Boat motion minimal (< 0.1 m/s)
- ✓ Distance stabilizes
- ✓ Tension balanced between wind and rode
- ✓ No chain motion

---

## Stage 7: Final Scope Deployment
**Duration:** 30-60 seconds  
**Rode Deployed:** 40-50m → Final (5:1 scope)  
**Purpose:** Deploy remaining chain to achieve final 5:1 scope ratio

### Scope Calculation
```
Scope = rode_deployed / (depth + bowHeight)
Target = 5:1 (typical for good holding with 2+ day storms)

Final rode = 5 × (depth + bowHeight)
Final rode = 5 × (3 + 2) = 25m

OR for specific conditions:
Final rode = 5 × water_depth = variable by location
```

### Expected Behavior
- Final chain deploys to achieve target scope
- Boat may drift another 1-2m as chain deploys
- Final holding pattern established
- System stabilizes at final anchor set point

### Success Criteria
- ✓ Final rode reaches target (5:1 scope or deployment limit)
- ✓ Boat position stabilizes
- ✓ All slack constraints satisfied
- ✓ Distance from anchor matches 5:1 scope requirement

---

## Overall Success Metrics

### Physics Must Satisfy
| Metric | Requirement | Typical | Warning |
|--------|-----------|---------|---------|
| Chain slack | ≥ 0 at all times | ~1-2m | < 0 = failure |
| Catenary limit | Distance ≤ limit | ✓ | Exceeds = failure |
| Deployment rate | Matches boat speed | 0.5m/10s | Too fast = bunch |
| Boat speed progression | Decreases over time | 0.8→0.1 m/s | Constant = issue |
| Rode tension | Increases smoothly | Gradual | Jerky = slack problem |

### Deployment Timeline
```
0-20s:    Stage 1 - Initial drop to 7m
20-22s:   Stage 2 - Orientation wait
22-60s:   Stage 3 - Initial dig deployment (7m → 15-20m)
60-90s:   Stage 4 - Initial dig hold
90-170s:  Stage 5 - Deep dig deployment (15-20m → 40-50m)
170-245s: Stage 6 - Deep dig hold
245-300s: Stage 7 - Final scope deployment
```

**Total Expected Duration:** 3-5 minutes

---

## Critical Physics Issues to Monitor

### Issue: Deployment Too Fast (Bunching Chain)
**Symptom:** Slack goes negative, distance exceeds catenary  
**Cause:** Deployment rate > boat drift speed  
**Fix:** Reduce winch speed or increase boat drift (motor assist)

### Issue: Deployment Too Slow (No Dig-In)
**Symptom:** Stage takes too long, boat barely moves  
**Cause:** Boat drift < deployment capability, winch stalls  
**Fix:** Increase wind model force or reduce boat mass

### Issue: Boat Moves Too Fast
**Symptom:** Distance exceeds catenary, slack goes negative  
**Cause:** Wind force or motor thrust too aggressive  
**Fix:** Reduce wind speed, increase boat mass, or increase water drag

### Issue: Boat Doesn't Move
**Symptom:** Rope stays at current stage, never progresses  
**Cause:** No wind force, motor not engaging, deployment blocked  
**Fix:** Ensure wind simulation active, motor working, INITIAL_DEPLOYMENT_LIMIT correct

---

## Testing Considerations

When running autoDrop tests at different wind speeds (5, 10, 15 kn):

### 5 Knot Wind
- **Expected:** Slow deployment, motor may need assistance
- **Watch for:** Very slow boat drift, stage timings extend
- **Risk:** Deployment takes too long, patience/timeout issues

### 10 Knot Wind  
- **Expected:** Moderate deployment, natural drift should work
- **Watch for:** Steady 0.5-0.8 m/s boat speed
- **Risk:** Least risky, good baseline behavior

### 15 Knot Wind
- **Expected:** Faster deployment, more boat movement
- **Watch for:** Risk of chain bunching if deployment rate too high
- **Risk:** Excessive drift, bunching if speed matching wrong

---

## Next Discussion Points

With this framework, we can now discuss:
- Which stage is currently failing in tests?
- Is the speed matching algorithm correct?
- Are stage timings appropriate?
- Should each stage trigger based on metrics vs. fixed duration?
- How should wind speed affect deployment rate in each stage?


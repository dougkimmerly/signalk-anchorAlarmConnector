# Anchor Deployment Simulation - Documentation

## ⚠️ CRITICAL CONCEPTS - READ FIRST

### Chain Deployment Physics (The Chain Controller Waits for Distance)

**During DEPLOYMENT (autoDrop):**
1. **Chain waits for boat to move AWAY** - The chain controller CANNOT deploy more chain until the boat moves farther away from the anchor
2. **Negative slack = BOAT TOO FAR** - If slack is negative, the boat has moved away TOO FAST, chain is fully extended
3. **Motor BACKWARD = Push boat AWAY** - During deployment, motor backward assists boat moving away from anchor
4. **If slack is negative during deployment**: Motor must STOP backward thrust (or the boat gets even farther away, making problem worse)

**During RETRIEVAL (autoRetrieve):**
1. **Chain waits for boat to move CLOSER** - The windlass pulls chain up as the boat moves toward the anchor
2. **Motor FORWARD = Push boat TOWARD** - Motor forward assists boat moving toward anchor
3. **Need positive slack** - Windlass needs slack to lift chain without fighting boat weight

**THE KEY RULE**:
- Deployment: Boat moves AWAY → chain follows → motor BACKWARD helps boat move away
- Retrieval: Boat moves TOWARD → chain follows → motor FORWARD helps boat move closer

## Overview

This is a physics-based simulation for testing anchor deployment behavior in SignalK. The simulator models wind-driven boat movement during anchor deployment, where anchor chain deploys as the boat drifts away from the anchor point due to wind forces.

## Architecture

### Core Files

1. **`plugin/testSimulation.js`** - The physics simulation engine

    - Runs within SignalK server
    - Calculates boat movement, forces, and position updates
    - Publishes boat position and anchor data to SignalK

2. **`validation/scripts/overnight_test_runner.py`** - Test harness

    - Python test runner that controls deployment scenarios
    - Runs autoDrop/autoRetrieve tests across wind/depth combinations
    - Collects simulation data into JSON files for analysis

3. **`DISABLED_FEATURES.md`** - Feature tracking document

    - Documents all currently disabled features
    - Tracks reason for each disabled feature
    - Provides re-enablement order for systematic validation

4. **`analyze_boat_movement.py`** - Data analysis script
    - Analyzes test result JSON files
    - Produces movement visualizations and phase analysis

## How the Simulation Works

### Motor Direction Terminology

**IMPORTANT**: Understanding motor direction is critical to avoid confusion:

- **Motor BACKWARD** = Thrust pushing boat AWAY from anchor (assists deployment)
- **Motor FORWARD** = Thrust pushing boat TOWARD anchor (assists retrieval)

These terms refer to the boat's motion relative to the anchor, NOT the boat's bow/stern orientation.

### Chain Slack Physics

**Chain slack** is the key metric for understanding anchor operations:

```
slack = rodeDeployed - distanceFromAnchor
```

**Slack Values**:
- **Positive slack (e.g., +3m)**: Chain has extra length lying on seabed or hanging loose
  - Good: Indicates chain being laid out properly on seabed
  - Catenary curve can form, providing shock absorption

- **Zero slack (0m)**: Chain is fully extended but not under tension
  - Acceptable: Chain forms straight line from anchor to boat
  - No catenary shock absorption available

- **Negative slack (e.g., -2m)**: **Physically impossible** - indicates simulation issue
  - Chain cannot stretch beyond its deployed length
  - Boat is moving away faster than chain can deploy
  - Shown in simulation to reveal control problems

**Why Slack Matters**:
- **During deployment**: We want to LAY CHAIN OUT EVENLY on the seabed with positive slack (1-3m ideal)
- **During retrieval**: We want to RETRIEVE CHAIN EVENLY with positive slack for windlass to lift it
- **At anchor**: Proper scope requires chain lying on seabed in catenary curve

### Deployment Goal: Even Chain Laying

The ideal deployment maintains **1-3 meters of slack** throughout:
- Chain pays out continuously at controlled rate
- Boat drifts away from anchor at slightly slower rate than chain deploys
- Chain settles evenly on seabed, not piled up or stretched tight
- Motor assists when wind is insufficient to maintain proper drift rate

**Common Mistake**: Fixed speed targets don't work because:
- In light wind, boat may drift too slowly → chain piles up → excess slack
- In strong wind, boat may drift too fast → chain can't keep up → negative slack
- **Solution**: Slack-based speed targeting adjusts motor dynamically

### Retrieval Goal: Even Chain Recovery

The ideal retrieval maintains **1-2 meters of slack** throughout:
- Windlass lifts chain continuously at controlled rate
- Boat moves toward anchor at slightly faster rate than chain retrieves
- Motor assists to keep slack positive so windlass can lift chain without load
- Chain comes aboard evenly, not in sudden jerks

### Slack-Based Motor Control Algorithm

**Deployment Motor Logic** (implemented in `testingSimulator.js:updateAutoMotor()`):

```javascript
// Step 1: Determine target speed based on current slack
if (slack < 1.0m) {
  targetSpeed = 0         // STOP - boat already moving away well
} else if (slack < 3.0m) {
  targetSpeed = 0.4 m/s   // MODERATE - gentle assistance needed
} else {
  targetSpeed = 0.8 m/s   // STRONG - boat falling behind chain deployment
}

// Step 2: Compare actual boat speed to target
if (boatSpeed < targetSpeed) {
  // Boat too slow - engage motor backward
  // Use proportional throttle based on speed deficit
  throttle = proportional(targetSpeed - boatSpeed)
  motorBackward(throttle)
} else {
  // Boat moving fast enough - ramp down motor
  rampDownAndStop()
}
```

**Why This Works**:
- **High slack** (chain piling up) → Motor increases target speed → More backward thrust → Boat moves away faster
- **Low slack** (chain tight) → Motor decreases target speed → Less backward thrust → Boat slows down
- **Negative slack** → Motor STOPS backward thrust → Boat drifts naturally → Chain controller waits for boat to come closer OR deploys when boat drifts farther
- Creates automatic feedback loop maintaining 1-3m slack

**CRITICAL**: Negative slack during deployment means boat is TOO FAR away (not too close). Motor backward would make this worse. We must stop motor and let natural forces (wind, drag) bring boat to correct distance.

**Retrieval Motor Logic**:
```javascript
if (slack < 1.0m) {
  // Chain tight - need more slack for windlass to lift
  motorForward(proportionalThrottle)
} else if (slack > 1.5m) {
  // Plenty of slack - reduce motor
  rampDownMotor()
}
```

### Physics Model

The simulation uses Newtonian mechanics to calculate boat movement:

```
Net Force = Wind Force + Water Drag + Motor Force + Constraint Forces
Acceleration = Net Force / Boat Mass
Velocity Update: v = v + a * Δt
Position Update: position = position + v * Δt
```

### Key Forces

#### 1. Wind Force

-   **Source**: Wind speed and direction (created and maintained in `plugin/testSimulation.js`)
-   **Direction Convention**:
    -   Wind direction 0° = wind FROM North (pushes boat SOUTH)
    -   Wind direction 180° = wind FROM South (pushes boat NORTH)
    -   Wind PUSHES in opposite direction: `pushDirection = (windDirection + 180) % 360`
-   **Magnitude**: `F = 0.5 * ρ * A * Cd * v²`
    -   ρ = air density (1.2 kg/m³)
    -   A = windage area (30 m² for sailboat)
    -   Cd = drag coefficient (1.0)
    -   v = wind speed in m/s

#### 2. Water Drag (Resistance)

-   **Model**: Quadratic drag opposing velocity
-   **Magnitude**: `F_drag = v * |v| * WATER_DRAG`
    -   WATER_DRAG coefficient = 20.0
    -   Increases with square of velocity
    -   Acts as primary speed limiter at higher velocities

#### 3. Motor Forces

**Motor Backward** (Deployment Assist):
- Pushes boat away from anchor when wind is insufficient
- Uses **slack-based speed targeting** to maintain even chain laying
- Target speeds adjust dynamically based on chain slack:
  - `slack < 1.0m` → Stop motor (boat moving away well enough)
  - `slack 1.0-3.0m` → Target 0.4 m/s (moderate assistance)
  - `slack > 3.0m` → Target 0.8 m/s (strong assistance)
- Prevents negative slack by increasing thrust when chain getting tight
- Ensures positive slack for proper chain laying on seabed

**Motor Forward** (Retrieval Assist):
- Pushes boat toward anchor during chain retrieval
- Maintains slack for windlass to lift chain without load
- Target: 1.0-1.5m slack during retrieval
- Proportional throttle based on slack deficit
- Stops when boat very close to anchor AND rode nearly retrieved

#### 4. Slack Constraint (Currently Disabled)

-   **Purpose**: Prevents boat from moving beyond rope length
-   **Status**: `DISABLE_SLACK_CONSTRAINT = true` (line 33)
-   **When enabled**: Would dampen velocity proportional to negative slack

### Coordinate System

-   **Latitude**: Increases NORTH
-   **Longitude**: Increases EAST
-   **Angle Convention**:
    -   Radians: 0 = North, π/2 = East, π = South, 3π/2 = West
    -   `sin(angle)` = East component
    -   `cos(angle)` = North component

### Anchor Position Establishment

**When Anchor Position is Set:**

When `dropAnchor` command is sent (rode > depth + bowHeight), the anchor alarm plugin immediately establishes the anchor position:
- **Latitude/Longitude**: Current boat GPS position
- **Altitude**: -(current depth + 2m bowHeight)

This happens as soon as the anchor hits the seabed, NOT after deployment completes. The altitude represents the anchor's depth below the water surface.

**Scope Calculation During Deployment:**

Once anchor position is established, scope can be calculated throughout deployment:
```javascript
scope = rodeDeployed / (anchorDepth + bowHeight)
```

Where:
- `anchorDepth` = abs(anchorPosition.altitude)
- `bowHeight` = 2m (distance from waterline to bow roller)

**Example at 12m depth:**
- Anchor hits seabed when rode > 14m (12m + 2m)
- `dropAnchor` sets anchor position with altitude = -14m
- At rode = 25m: scope = 25 / (14 + 2) = 1.56:1
- At rode = 60m: scope = 60 / (14 + 2) = 3.75:1
- Target: rode = 80m: scope = 80 / (14 + 2) = 5.0:1

### Virtual vs Real Anchor

-   **Real Anchor** (`anchorPos`): Set by alarm system when dropAnchor called, used for distance calculations
-   **Virtual Anchor** (`virtualAnchorLat/Lon`): Set when deployment starts
    -   Prevents physics explosions when boat manually repositioned
    -   Stays fixed during deployment for consistent force calculations
    -   Should always be the same as `anchorPos` unless a manual movement is being completed

## Global State Variables

These variables persist across physics loop iterations but must be reset between tests:

```javascript
let boatVelocityX = 0 // m/s, east-west velocity
let boatVelocityY = 0 // m/s, north-south velocity
let currentLat = null // current boat latitude
let currentLon = null // current boat longitude
let virtualAnchorLat = null // anchor position for physics calculations
let virtualAnchorLon = null
let previousRodeDeployed = 0 // for detecting new deployments
let motoringBackwardsActive = false
let motoringActive = false
```

### Critical Fix: Velocity Reset on New Deployment

**Lines 187-192** reset velocities when a new deployment starts:

```javascript
if (currentRodeDeployed > 0 && previousRodeDeployed === 0) {
    boatVelocityX = 0
    boatVelocityY = 0
    // New deployment detected - clear accumulated momentum
}
```

This fix prevents alternating N-S-N movement patterns across consecutive tests.

## Testing System

### Test Flow

```
1. Start Test
   ↓
2. Stop Chain Controller (python3 stop_chain.py)
   ↓
3. Reset Anchor to 0m Rode (python3 reset_anchor.py)
   ↓
4. Run AutoDrop Deployment (python3 simple_autodrop_test.py)
   ├─ Set wind speed & direction
   ├─ Start autoDrop command
   ├─ Monitor until target scope (5:1 = 25m) or timeout
   └─ Save test data to JSON
   ↓
5. Analyze Results (python3 analyze_boat_movement.py)
```

### Test Configuration

**File**: `validation/scripts/overnight_test_runner.py`

Key parameters:

```python
'wind_speed_kn': 20              # Wind speed (knots)
'wind_direction': 180            # Wind from South
timeout_seconds: 240             # Max test duration (4 minutes)
target_scope: 5.0                # Target deployment (5:1 scope)
```

### Test Output Format

**Location**: `validation/data/overnight_tests_*/raw_data/*.json`

Sample structure:

```json
{
  "test_type": "autoDrop_simplified",
  "wind_speed_kn": 20,
  "samples": [
    {
      "latitude": 43.59727878611452,
      "longitude": -79.50728825074235,
      "boat_speed": 0.115,
      "boat_heading": 182.64°,
      "distance": 0.0,           // distance from anchor (m)
      "rode_deployed": 0,        // chain deployed (m)
      "chain_slack": 0,          // rode - distance
      "depth": 3.0,
      "time_sec": 0.011
    },
    ... (repeated every ~0.1 seconds for 240 seconds)
  ]
}
```

## Key Behaviors

### Typical Deployment Phases

Analysis of test `autodrop_20kn_20251201_024728.json` reveals three distinct phases:

**Phase 1: Acceleration (0-42s)**

-   Boat accelerates from rest
-   Distance: 0m → 14.4m
-   Rode deploys: 0m → 10m
-   Speed: accelerating to 1.1 m/s
-   Wind force overcomes initial inertia ✓

**Phase 2: Deceleration (42-110s)**

-   Boat speed collapses dramatically
-   Distance: 14.4m → 23.9m (only 9.5m additional)
-   Rode deploys: 10m → 20m
-   Speed: drops from 1.1 m/s to 0.17 m/s
-   **ISSUE**: Boat moves less than chain deployed

**Phase 3: Complete Stall (110-182s)**

-   Boat speed → 0.01 m/s (essentially stopped)
-   Distance frozen at 23.2m
-   Rode frozen at 20.0m
-   Chain slack: -4.8m (boat 4.8m beyond rope end)
-   Duration: 72 seconds of zero movement
-   **ROOT CAUSE**: Unknown damping mechanism

**Phase 4: Resume (182-240s)**

-   Chain controller deploys more rope
-   Boat resumes movement at normal speed
-   Distance: 23.2m → 28.2m
-   Final rode: 25.0m (target reached) ✓

### Known Issues

#### Issue 1: Phase 3 Stalling

**Symptom**: Boat velocity collapses when distance > rode deployed

**Force Analysis**:

-   Wind force (20kn): ~1,900 N northward
-   Expected acceleration: 1,900 N / 15,875 kg = 0.12 m/s²
-   Actual: speed → 0.006 m/s (velocity being damped)

**Suspected Causes**:

1. Slack constraint application (despite DISABLE_SLACK_CONSTRAINT=true)
2. Hidden damping mechanism in constraint logic
3. Position correction pulling boat back toward anchor
4. Virtual anchor behavior creating constraint

**Investigation Status**: Pending - constraint block analysis incomplete

#### Issue 2: Gradual Movement Bug (FIXED)

**Symptom**: Boat moving in wrong direction during certain conditions
**Status**: DISABLED (line 524: `if (false && ...`)
**Root Cause**: Direction inversion bug in gradual move calculation
**Impact**: Single line disable fixed full 5:1 scope deployment!

#### Issue 3: Motor Interference (FIXED)

**Symptom**: Motor backward hindering deployment by 7.2m
**Status**: DISABLED (DISABLE_MOTOR_ACTIVITY = true)
**Result**: Motor OFF achieves 20m rode vs Motor ON achieves 12.8m

#### Issue 4: Velocity Accumulation (FIXED)

**Symptom**: Consecutive tests produce N-S-N alternating pattern
**Root Cause**: Global velocities not reset between tests
**Status**: FIXED with deployment detection at lines 187-192
**Verification**: 3 consecutive tests now all produce consistent NORTH movement

## Disabled Features

See `DISABLED_FEATURES.md` for complete tracking.

Current disabled features:

1. **Motor Activity** - Hindering wind-driven movement
2. **Wind Direction Randomization** - Complicates analysis
3. **Gradual Movement** - Causes direction inversion bug
4. **Slack Constraint** - Limiter set, but unknown damping still active

Re-enablement order (suggested):

1. Validate: Boat moves NORTH consistently (current state ✓)
2. Re-enable: Wind direction randomization (±2°)
3. Re-enable: Gradual movement (WITH FIX for direction)
4. Re-enable: Slack constraint (WITH TUNING for 25m target)
5. Re-enable: Motor backward (WITH LOWER GAINS)

## Running Tests

### Single Test

```bash
cd /home/doug/src/signalk-anchorAlarmConnector/validation/scripts
python3 stop_chain.py
python3 reset_anchor.py
python3 test_deploy_retrieve.py
```

### Full Test Suite

```bash
cd /home/doug/src/signalk-anchorAlarmConnector/validation/scripts
python3 overnight_test_runner.py
```

### Quick Validation

```bash
cd /home/doug/src/signalk-anchorAlarmConnector/validation/scripts
python3 quick_validation_test.py
```

## Important Constants

**Physics Parameters** (testSimulation.js):

-   `BOAT_MASS = 15875 kg` (35,000 lbs)
-   `WATER_DRAG = 20.0` (quadratic drag coefficient)
-   `METERS_TO_LAT = 0.000009` (lat degrees per meter)
-   `METERS_TO_LON = 0.0000125` (lon degrees per meter)
-   `DT = 0.05` (time step in seconds)

**Deployment Parameters**:

-   `currentDepth = 3.0 m` (water depth)
-   `bowHeight = 0.5 m` (bow height above water)
-   `targetRode = (depth + bow) * 5 = 17.5 m` (5:1 scope = 25m)
-   `constraintStartRode = 2.625 m` (15% of target)
-   `constraintEndRode = 17.5 m` (100% of target)

## Key Test Results

### Test: `autodrop_20kn_20251201_024728.json`

-   Wind: 20 knots from South (direction 180°)
-   Motor: OFF
-   Gradual Move: DISABLED
-   Slack Constraint: DISABLED
-   Result: **25.0m rode deployed** (5:1 scope target ACHIEVED ✓)
-   Pattern: N→S→N in Phase 2-3, then resumes north in Phase 4

### Consistency Test (3 consecutive runs)

-   Test 1: NORTH bearing 19°, 28.1m distance
-   Test 2: NORTH bearing 19°, 28.1m distance
-   Test 3: NORTH bearing 19°, 28.1m distance
-   Pattern: **Consistent NORTH across all tests** ✓ (velocity reset working)

## Debugging Tips

### Enable Constraint Logging

Change line 33:

```javascript
let DISABLE_SLACK_CONSTRAINT = false // Enable constraint
```

This will add console output:

```
>>> CONSTRAINT APPLIED: slack=-2.90m, strength=1.00, velBefore=(0.5, 1.2)
>>> VELOCITY DAMPENED: factor=0.300, velAfter=(0.15, 0.36)
```

### Analyze Movement Phases

Use `analyze_boat_movement.py` to visualize:

-   Boat speed over time
-   Distance from anchor over time
-   Rode deployed over time
-   Chain slack over time
-   Phase transitions (acceleration → deceleration → stall → resume)

### Check Velocity Reset

Search testSimulation.js output for:

```
>>> RESET VELOCITIES: New anchor deployment detected
```

This confirms velocities cleared at deployment start.

### Force Analysis

Calculate expected vs actual acceleration:

```
Expected: F_wind / mass = 1900 / 15875 = 0.12 m/s²
Actual: (speed_t2 - speed_t1) / Δt
```

If actual << expected, constraint is active or damping is present.

## Next Steps for Development

1. **Investigate Phase 3 Stall Mechanism**

    - Determine if slack constraint is still active despite DISABLE flag
    - Check if position correction (lines 640-641) is being executed
    - Verify virtual anchor behavior isn't constraining movement
    - Add aggressive logging to constraint application

2. **Fix Gradual Movement Direction Inversion**

    - Re-enable gradual movement (line 524)
    - Fix angle inversion when moving away from anchor
    - Test with gradual move enabled

3. **Tune Slack Constraint**

    - Once movement is consistent, re-enable slack constraint
    - Adjust constraint strength ramping
    - Target: smooth deployment to 25m without stalling

4. **Re-enable Motor Logic**

    - Lower motor backward gains
    - Test interaction with slack constraint
    - Validate that motor supplements (not hinders) wind movement

5. **Validate with Wind Variation**
    - Re-enable ±2° wind direction randomization
    - Run 10+ consecutive tests
    - Verify consistent deployment across all variations

## References

-   **SignalK Guide**: `docs/SIGNALK_GUIDE.md` - Quick reference for SignalK concepts, data models, APIs, and unit conversions used throughout this project
-   **SignalK Anchor Data**: `navigation.anchor.*` paths
-   **Physics Model**: Newtonian mechanics with quadratic drag
-   **Catenary Formula**: `maxSwingRadius = sqrt(rode² - depth²)`
-   **Coordinate System**: WGS84 latitude/longitude with local meter conversion

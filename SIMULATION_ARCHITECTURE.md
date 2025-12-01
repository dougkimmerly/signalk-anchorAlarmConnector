# Simulation Architecture - CRITICAL KNOWLEDGE

## What the Simulation Program PUBLISHES to SignalK
(These are values the simulation CREATES and CONTROLS)

- `navigation.position` (latitude, longitude) - boat position, driven by wind forces
- `environment.wind.speedTrue` - wind speed in m/s (simulated, starts at 10 knots + random gusts)
- `environment.wind.directionTrue` - wind direction in radians (simulated, from 180° south, with random shifts)
- `navigation.headingTrue` - boat heading (boat acts as weathervane, points into wind)
- `navigation.speedOverGround` - calculated boat speed from velocity vectors
- `environment.depth.belowSurface` - water depth (fixed at 3m in test)
- `navigation.anchor.position` - anchor position (auto-set to boat position when chain deploying)

## What the Simulation RECEIVES from SignalK (External Sources)
(These come from chain controller or external systems)

- `navigation.anchor.rodeDeployed` - how much chain is deployed (meters)
- `navigation.anchor.chainSlack` - calculated slack from chain controller
- `navigation.anchor.chainDirection` - 'down' (deploying), 'up' (retrieving), or idle/stopped
- `navigation.anchor.command` - external commands (autoDrop, autoRetrieve, stop)

## CRITICAL: chainDirection Behavior

**Important**: `chainDirection` is ONLY:
- 'down' when the chain motor is ACTIVELY deploying
- 'up' when the chain motor is ACTIVELY retrieving
- Idle/stopped/null the REST OF THE TIME

**DO NOT use chainDirection to infer what's happening.** The simulation must use OTHER logic:
- Check `rodeDeployed` value directly
- Check if anchor has been set
- Monitor boat movement and distance to determine phase
- The slack constraint must work regardless of chainDirection state

## Simulation Physics Responsibility

The simulation is responsible for:
1. **Wind force calculation** - converts wind direction to X/Y force components
2. **Boat movement** - integrates wind force with drag and constraints
3. **Position updates** - converts velocity to lat/lon changes
4. **Slack constraint** - prevents boat from exceeding rope length based on slack value
5. **Heading** - boat acts as weathervane (points into wind source)

## Critical Bug History

**Wind Force Direction Bug**: Initially had `windAngleRad = (windDirection + 180) % 360` which inverted the wind direction.
- Wind from 180° (south) was pushing SOUTH instead of NORTH
- Fix: Calculate `windPushDirection = (windDirection + 180) % 360` FIRST, then convert to radians
- This converts "direction wind comes FROM" to "direction wind pushes TO"

## Coordinate System

- Latitude increases NORTH, decreases SOUTH
- Longitude increases EAST, decreases WEST
- Wind direction 0° = North, 90° = East, 180° = South, 270° = West
- `sin(angle)` gives X (East) component
- `cos(angle)` gives Y (North) component

## Slack Constraint Logic

**The constraint should be based ONLY on slack value, not chainDirection:**

```
chainSlack = rodeDeployed - distanceFromAnchor

if chainSlack <= 0:
    apply infinite constraint (prevent boat moving beyond rope)
else if 0 < chainSlack < depth:
    apply proportional constraint (scales from 0% to 100% as slack increases)
else if chainSlack >= depth:
    apply no constraint (plenty of rope available)
```

**The constraint strength should scale with deployment progress:**
- Start applying constraint at 15% of 5:1 target scope
- Increase linearly to 100% at full 5:1 target scope
- Below 15%: No constraint (allow natural wind drift during initial deployment)

## Test Framework vs Simulation

**Test framework reads from SignalK:**
- position (to calculate boat movement)
- chainSlack (published by chain controller, calculated from distance)
- rodeDeployed (from chain controller)
- distance (calculated as `sqrt((lat-anchorLat)² + (lon-anchorLon)²)`)

**Test framework DOES NOT read:**
- Wind data (it's in SignalK but test doesn't use it)
- Heading (it's published but test doesn't validate against it)

The test scores on:
1. Whether boat moved in expected direction (bearing 0° = north)
2. How much chain deployed (should reach 25m for 5:1 scope)
3. Movement direction consistency
4. Stability (no rapid speed changes)

## Current Known Issues

1. **Boat moving SOUTH instead of NORTH** - even with wind from south (180°), boat drifts south when it should drift north
   - Suspect: Wind force sign, coordinate system confusion, or constraint forcing boat back
   - Need to verify: wind force Y component is actually positive, and not being negated elsewhere

2. **Chain only deploys to 14-20m instead of 25m** - slack constraint or other factors limiting deployment
   - Deployed to 7m before fix
   - Deployed to 20m with first wind force fix
   - Deployed to 14.5m with full wind fix
   - Needs investigation of what's limiting further deployment

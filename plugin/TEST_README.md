# Test Simulation

This directory contains test simulation code for development and testing purposes.

## Files

- **testSimulation.js** - Wind-based physics simulation for anchor behavior testing

## Usage

### Enabling/Disabling Test Mode

Test mode is now controlled via the plugin configuration in the SignalK server UI:

1. Navigate to **Server → Plugin Config → Anchor Alarm Connector**
2. Toggle the **"Enable Test Simulation"** checkbox
3. Click **Submit** and restart the plugin

**When enabled (`testMode: true`):**
- Wind-based physics simulation runs automatically
- Simulated position, depth, wind, and heading data
- Console logs: `"Test mode enabled - starting wind-based anchor simulation"`
- Zone testing endpoints are available

**When disabled (`testMode: false`, default):**
- No simulation runs
- Plugin operates with real vessel data from sensors
- Console logs: `"Test mode disabled - running in production mode"`

No code changes are needed to switch between test and production modes.

## Test Simulation Features

The test simulation provides realistic anchor behavior for testing the chain controller:

### Wind Simulation
- Starts at 10 knots from 180° (blowing from south)
- Random gusts: ±3 knots variation
- Gradual wind shifts: ±2° every 10 seconds
- Wind speed range: 5-20 knots

### Boat Physics
- Wind force (proportional to wind speed²)
- Rode tension (spring-like restoring force)
- Water drag (velocity damping)
- Realistic mass/acceleration dynamics

**Physics Stability Features:**
- **Virtual anchor position**: Separate from SignalK anchor position to prevent physics explosions when anchor is manually repositioned
- **Smoothed rode length**: Gradual changes prevent sudden force spikes
- **Grace period**: 60 iterations (~30 seconds) after manual position changes where physics forces are reduced
- **Velocity limits**: Prevents unrealistic acceleration from bad data

### Test Scenarios

You can modify the simulation parameters in `testSimulation.js`:

```javascript
// Physics constants (lines 34-37)
const BOAT_MASS = 5000          // kg - adjust for your boat size
const WATER_DRAG = 0.15         // drag coefficient
const RODE_SPRING_CONSTANT = 0.8 // spring stiffness
const DT = 0.5                  // time step in seconds

// Initial conditions (lines 11-13)
const testDepth = 5              // meters
const initialLat = 43.59738      // starting latitude
const initialLon = -79.5073      // starting longitude

// Wind settings (lines 44-45)
windSpeed = 10                   // knots
windDirection = 180              // degrees true
```

### What to Expect

When the simulation runs:
1. Boat will drift downwind from the anchor position
2. As rode tension increases, boat will slow and settle
3. Wind gusts will cause surge and fall-back movements
4. Wind shifts will cause the boat to swing around the anchor
5. Chain controller should automatically adjust rode deployed

### Zone Testing Endpoints

The plugin provides HTTP endpoints to test alarm zone behavior by moving the boat to specific zones:

**Move to Warning Zone:**
```bash
curl -X PUT http://localhost:80/plugins/signalk-anchoralarmconnector/movetowarning
```
- Positions boat at far end of warning zone (1m before emergency threshold)
- Gives room for natural drift while staying in warning zone
- Returns: `"Moved to warn zone (X.Xm from anchor)"`

**Move to Alarm Zone (Emergency):**
```bash
curl -X PUT http://localhost:80/plugins/signalk-anchoralarmconnector/movetoalarm
```
- Positions boat just past emergency threshold (1m into emergency zone)
- Triggers emergency alarm immediately
- Returns: `"Moved to alarm zone (X.Xm from anchor)"`

**How It Works:**
1. Reads current alarm zone configuration from `navigation.anchor.meta.zones`
2. Calculates target bearing from boat to anchor
3. Sets new position at target distance along that bearing
4. Maintains realistic heading (boat points toward anchor)
5. Uses virtual anchor position to prevent physics explosions after manual moves

**Note:** These endpoints are available when the anchor is set and alarm zones are configured. They work in both test mode and production (for testing with real sensor data).

### Monitoring the Simulation

The simulation logs periodic updates:
```
Wind update: 12.3 knots from 185°
Boat physics: dist=8.2m, maxSwing=12.5m, vel=(0.15,0.08)m/s, wind=12.3kt@185°
```

- **dist**: Current distance from anchor
- **maxSwing**: Maximum swing radius based on rode deployed
- **vel**: Boat velocity (east, north) in m/s
- **wind**: Current wind speed and direction

## SignalK Paths Updated

The test simulation updates these SignalK paths:

- `environment.depth.belowSurface` - Constant 5m for testing
- `navigation.position` - Updated every 0.5s based on physics
- `navigation.headingTrue` - Set to 0° (north)
- `environment.wind.speedTrue` - Updated every 10s
- `environment.wind.directionTrue` - Updated every 10s

## Integration with Chain Controller

The simulation is designed to trigger automatic chain control:

1. **Initial anchor drop**: Boat drifts as wind pushes it
2. **Rode deployment**: Controller should pay out chain as needed
3. **Wind increases**: More chain deployed automatically
4. **Wind decreases**: Chain retrieved as boat falls back
5. **Wind shift**: Boat swings, chain adjusts for new position

## Troubleshooting

**Simulation not running:**
- Check console for "Starting wind-based anchor test simulation..."
- Verify `testSimulation.js` is in the plugin directory
- Ensure the require statement is not commented out

**Boat not moving:**
- Wait for anchor to be set (anchor position must exist)
- Check that rode is deployed (navigation.anchor.rodeDeployed > 0)

**Unrealistic behavior:**
- Adjust physics constants (BOAT_MASS, WATER_DRAG, RODE_SPRING_CONSTANT)
- Modify wind speed range in the gust calculation
- Change DT (time step) for faster/slower simulation

**Zone testing endpoints not working:**
- Ensure anchor is set (`navigation.anchor.position` must exist)
- Check alarm zones are configured (`navigation.anchor.meta.zones`)
- Verify plugin is running and accessible
- Check response message for specific errors

**Physics explosion after using zone endpoints:**
- This should no longer occur due to virtual anchor position
- Grace period reduces forces for ~30 seconds after manual moves
- If still occurring, check console for NaN/Infinity warnings

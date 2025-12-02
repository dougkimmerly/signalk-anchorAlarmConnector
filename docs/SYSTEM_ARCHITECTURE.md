# Integrated Anchor Management System Architecture

## System Overview

This is a complete anchor management system integrating hardware chain counter, SignalK server, anchor alarm, and automation plugins.

## Components

### 1. Chain Controller (ESP32 + SensESP)
**Location**: `/home/doug/src/SensESP-chain-counter` (Mac)
**Hardware**: ESP32 microcontroller with SensESP framework
**Repository**: `git@github.com:dougkimmerly/SensESP-chain-counter.git`

#### Hardware Inputs
- **Hall Effect Sensor** (GPIO 27): Counts gypsy rotations
- **UP Button** (GPIO 23): Manual windlass up control
- **DOWN Button** (GPIO 25): Manual windlass down control
- **RESET Button** (GPIO 26): Reset chain counter to zero

#### Hardware Outputs
- **UP Relay** (GPIO 16): Controls windlass motor (up)
- **DOWN Relay** (GPIO 19): Controls windlass motor (down)

#### Key Features
- **Chain Counting**: Multiplies gypsy rotations by circumference (default 0.25m)
- **Non-volatile Storage**: Saves chain length to ESP32 Preferences
- **Speed Learning**: Tracks actual windlass speed (up/down) and adjusts timeouts
- **Safety Limits**:
  - Minimum: 2m (stops 2m before fully up)
  - Maximum: 80m (stops 5m before max)
- **Automatic Control**: Responds to SignalK commands

#### SignalK Data Published (every 11 seconds)
```javascript
navigation.anchor.rodeDeployed        // Chain length in meters
navigation.anchor.chainDirection      // "up", "down", or "free fall"
navigation.anchor.command             // Current command state
navigation.anchor.chainSlack          // Calculated horizontal slack
```

#### SignalK Commands Received (via PUT)
```javascript
navigation.anchor.command = "drop"        // Initial drop (depth + 4m)
navigation.anchor.command = "raise10"     // Raise 10m
navigation.anchor.command = "lower10"     // Lower 10m
navigation.anchor.command = "STOP"        // Emergency stop
navigation.anchor.command = "autoDrop"    // Automated deployment sequence
navigation.anchor.rodeDeployed = 1        // Reset counter (special value)
```

---

### 2. SignalK Server (Raspberry Pi)
**Location**: Raspberry Pi
**Port**: 80 (HTTP)
**Role**: Central data hub and communication backbone

#### Key Features
- Aggregates data from multiple sources (chain counter, GPS, depth sensor, etc.)
- Provides REST API for data access and control
- WebSocket support for real-time updates
- OAuth/JWT authentication
- Hosts plugins (anchor alarm, anchor alarm connector)

---

### 3. Anchor Alarm Plugin
**Name**: `signalk-anchoralarm-plugin`
**Repository**: https://github.com/sbender9/signalk-anchoralarm-plugin
**Web UI**: `http://localhost:80/signalk-anchoralarm-plugin/`

#### Key Features
- Interactive map showing boat position and anchor
- Configurable alarm zones (normal, warning, emergency)
- Visual/audio alarms when boat drifts
- Alarm radius based on rode length or manual setting

#### SignalK Paths Managed
```javascript
navigation.anchor.position        // Anchor GPS coordinates {lat, lon, altitude}
navigation.anchor.meta.zones      // Alarm zones configuration
```

#### HTTP API Commands
```javascript
POST /plugins/anchoralarm/dropAnchor        // Mark anchor dropped at current position
POST /plugins/anchoralarm/raiseAnchor       // Mark anchor raised, disable alarm
POST /plugins/anchoralarm/setRodeLength     // Update alarm radius
     Body: {"length": 50}
POST /plugins/anchoralarm/setManualAnchor   // Set anchor with depth
     Body: {"anchorDepth": 5, "rodeLength": 50}
```

---

### 4. Anchor Alarm Connector Plugin
**Location**: `/home/doug/src/signalk-anchorAlarmConnector` (RPi)
**Role**: Automation bridge between chain counter and anchor alarm

#### Core Logic

**Automatic Anchor Drop Detection**
```javascript
IF rodeDeployed > (depth + bowHeight) AND anchor not dropped
  → Send dropAnchor command
  → Record lastChainMove timestamp
  → Set anchorDepth
```

**Automatic Anchor Raise Detection**
```javascript
IF rodeDeployed < (depth + bowHeight) AND anchor is dropped
  → Send raiseAnchor command
  → Reset anchorSet flag
  → Set scope to 0
```

**Automatic Anchor Setting (After Settling)**
```javascript
IF no chain movement for 120 seconds AND anchor dropped
  → Calculate anchor depth from position altitude
  → Send setManualAnchor (depth + rode length)
  → Send setRodeLength to update alarm radius
  → Calculate and publish scope
  → Mark anchor as "set"
```

#### SignalK Paths Monitored
```javascript
navigation.anchor.rodeDeployed      // From chain counter
navigation.anchor.position          // From anchor alarm
navigation.anchor.rodeLength        // Total available chain
navigation.anchor.distanceFromBow   // Current distance from anchor
navigation.anchor.command           // Commands from external systems
environment.depth.belowSurface      // Water depth from sensor
design.bowAnchorHeight             // Bow height above waterline (default 2m)
navigation.position                 // Vessel GPS position
```

#### SignalK Paths Published
```javascript
navigation.anchor.autoReady         // System health indicator
navigation.anchor.scope             // Calculated scope (rode/depth)
```

#### Test Simulation Features
- **Wind-based physics**: Realistic boat drift using aerodynamic forces
- **Catenary calculations**: Proper swing radius based on rode/depth
- **Zone testing**: Move boat to warning/alarm zones via HTTP endpoints
- **Test mode toggle**: Enable/disable via plugin settings

#### HTTP API Endpoints
```javascript
PUT /plugins/signalk-anchoralarmconnector/movesouth
    Body: {"distance": 5}  // Move south by 5m

PUT /plugins/signalk-anchoralarmconnector/movetowarning
    // Move boat to middle of warning zone

PUT /plugins/signalk-anchoralarmconnector/movetoalarm
    // Move boat into alarm zone (emergency)
```

---

## Data Flow

### Normal Operation (Deploying Anchor)

```
1. USER DEPLOYS CHAIN
   ↓
2. [Chain Controller] Hall sensor counts rotations
   ↓
3. [Chain Controller] Calculates: rodeDeployed = rotations × circumference
   ↓
4. [Chain Controller] Publishes to SignalK every 11s:
      navigation.anchor.rodeDeployed = 14m
   ↓
5. [SignalK Server] Broadcasts to subscribers
   ↓
6. [Anchor Alarm Connector] Monitors rodeDeployed
   ↓
7. [Anchor Alarm Connector] Detects: rodeDeployed > depth + bowHeight
   ↓
8. [Anchor Alarm Connector] POST to anchor alarm:
      /plugins/anchoralarm/dropAnchor
   ↓
9. [Anchor Alarm Plugin] Records anchor position from GPS
      navigation.anchor.position = {lat, lon, altitude}
   ↓
10. [Anchor Alarm Connector] Waits for 120s of no chain movement
   ↓
11. [Anchor Alarm Connector] POST to anchor alarm:
       /plugins/anchoralarm/setManualAnchor {depth, rodeLength}
       /plugins/anchoralarm/setRodeLength {length}
   ↓
12. [Anchor Alarm Plugin] Activates alarm with calculated radius
   ↓
13. [Anchor Alarm Connector] Publishes:
       navigation.anchor.scope = rodeDeployed / (depth + bowHeight)
```

### Automated Windlass Control (via Chain Controller)

```
1. EXTERNAL COMMAND (from app, plugin, etc.)
   ↓
2. PUT to SignalK:
      navigation.anchor.command = "drop"
   ↓
3. [SignalK Server] Broadcasts to listeners
   ↓
4. [Chain Controller] Receives command
   ↓
5. [Chain Controller] Reads environment.depth.belowSurface
   ↓
6. [Chain Controller] Calculates target: depth + 4m
   ↓
7. [Chain Controller] Activates DOWN relay
   ↓
8. [Windlass Motor] Lowers anchor chain
   ↓
9. [Hall Sensor] Counts rotations → updates rodeDeployed
   ↓
10. [Chain Controller] Monitors current position via accumulator
   ↓
11. [Chain Controller] When target reached → deactivates relay
   ↓
12. [Anchor Alarm Connector] Detects deployment → triggers alarm setup
```

---

## Configuration

### Chain Controller (ESP32)
- **Gypsy Circumference**: 0.25m (default)
- **Max Chain Length**: 80m
- **Min Chain Stop**: 2m before fully up
- **GPIO Pins**: Configurable via SensESP UI
- **Debounce Times**: 15ms default for all inputs
- **Free Fall Delays**: 2s for UP/DOWN buttons

### Anchor Alarm Connector (SignalK Plugin)
- **Server Base URL**: `http://localhost:80`
- **Client ID**: `signalk-anchor-alarm-connector`
- **Test Mode**: `false` (default - disable for production)
- **Settling Timeout**: 120 seconds
- **Drop Command Debounce**: 5 seconds

### Anchor Alarm Plugin
- **Alarm Radius**: Default 5× water depth
- **Zone Configuration**: Normal → Warning → Emergency
- **Update Rate**: Position/heading every 1.5 seconds

---

## System Health Indicators

### `navigation.anchor.autoReady`
Published by Anchor Alarm Connector, indicates all systems operational:

```javascript
autoReady = true IF:
  - Position updated < 30s ago
  - Depth updated < 30s ago
  - Chain counter connected < 60s ago
```

### Chain Counter Connection
- Publishes data every 11 seconds
- If no updates received for >60s, indicates hardware issue

---

## Testing

### Test Simulation (Anchor Alarm Connector)
Enable via plugin settings: `testMode: true`

**Features**:
- Wind-based physics (10 knots from 180°)
- Boat mass: 15,875 kg (35,000 lbs)
- Realistic forces: wind, rode tension, water drag
- Automatic heading toward anchor
- Catenary calculations for swing radius

**Zone Testing**:
```bash
# Move to warning zone
curl -X PUT http://localhost:80/plugins/signalk-anchoralarmconnector/movetowarning

# Move to alarm zone
curl -X PUT http://localhost:80/plugins/signalk-anchoralarmconnector/movetoalarm
```

---

## Troubleshooting

### Chain Counter Not Updating
- Check ESP32 power and WiFi connection
- Verify hall sensor GPIO and wiring
- Check SignalK server connectivity
- Look for updates on `navigation.anchor.rodeDeployed`

### Anchor Not Auto-Dropping
- Verify `rodeDeployed > depth + bowHeight`
- Check depth sensor data available
- Ensure anchor alarm plugin running
- Check 5s debounce hasn't blocked command

### Windlass Not Responding to Commands
- Verify relay wiring (GPIO 16 UP, GPIO 19 DOWN)
- Check command reaching chain controller
- Verify chain not at safety limits (2m min, 75m max)
- Check for active timeout delays

### Alarm Not Setting After 2 Minutes
- Verify no chain movement for 120s
- Check anchor position has altitude data
- Ensure `anchorDropped = true`
- Verify depth sensor working

---

## Future Enhancements

- [ ] Configurable settling timeout (currently hardcoded 120s)
- [ ] Multi-anchor support
- [ ] Wind compensation for alarm radius
- [ ] Rode angle/catenary calculations for more accurate scope
- [ ] Alert notifications for anchor dragging
- [ ] Integration with autopilot for automatic repositioning

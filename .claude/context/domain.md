# Domain Context

> SignalK paths, API endpoints, and authentication. Reference for working with SignalK.

## SignalK Paths - This Plugin

### Input Paths (Monitored)

| Path | Type | Source | Purpose |
|------|------|--------|---------|
| `navigation.anchor.rodeDeployed` | number (m) | Chain counter | Current chain out |
| `navigation.anchor.rodeLength` | number (m) | Config | Total available chain |
| `navigation.anchor.position` | object | Anchor alarm | GPS {lat, lon, altitude} |
| `navigation.anchor.distanceFromBow` | number (m) | Calculated | Distance to anchor |
| `navigation.anchor.command` | string | External | autoDrop/autoRetrieve/idle |
| `navigation.anchor.chainDirection` | string | Chain counter | up/down/idle (active only) |
| `environment.depth.belowSurface` | number (m) | Depth sensor | Water depth |
| `design.bowAnchorHeight` | number (m) | Config | Bow height (default: 2) |
| `navigation.position` | object | GPS | Vessel position |
| `navigation.headingTrue` | number (rad) | Compass | Vessel heading |

### Output Paths (Published)

| Path | Type | Purpose |
|------|------|---------|
| `navigation.anchor.autoReady` | boolean | System health indicator |
| `navigation.anchor.scope` | number | Calculated scope ratio |
| `navigation.anchor.setAnchor` | boolean | Anchor alarm active state |

## Anchor Alarm Plugin API

Base URL: `http://localhost:80/plugins/anchoralarm`

### Commands (POST)

```bash
# Mark anchor dropped at current GPS
POST /plugins/anchoralarm/dropAnchor

# Mark anchor raised, disable alarm
POST /plugins/anchoralarm/raiseAnchor

# Set alarm radius from rode length
POST /plugins/anchoralarm/setRodeLength
Content-Type: application/json
{"length": 50}

# Set anchor with depth (manual mode)
POST /plugins/anchoralarm/setManualAnchor
Content-Type: application/json
{"anchorDepth": 5, "rodeLength": 50}

# Calculate radius from current position
POST /plugins/anchoralarm/setRadius
```

### Web Interface

- **Map UI**: `http://localhost:80/signalk-anchoralarm-plugin/`
- **With OpenSeaMap**: `http://localhost:80/signalk-anchoralarm-plugin/?openseamap`
- **With Satellite**: `http://localhost:80/signalk-anchoralarm-plugin/?satellite`

## This Plugin's HTTP API

Base URL: `http://localhost:80/plugins/signalk-anchoralarmconnector`

### Endpoints

```bash
# Get simulation state
GET /plugins/signalk-anchoralarmconnector/simulation/state

# Move boat south (testing)
PUT /plugins/signalk-anchoralarmconnector/movesouth
Content-Type: application/json
{"distance": 5}

# Move to warning zone (testing)
PUT /plugins/signalk-anchoralarmconnector/movetowarning

# Move to alarm zone (testing)
PUT /plugins/signalk-anchoralarmconnector/movetoalarm
```

## SignalK Authentication

### Get JWT Token

```bash
TOKEN=$(curl -s -X POST http://localhost:80/signalk/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"signalk"}' | jq -r '.token')
```

### Use Token in Requests

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:80/plugins/signalk-anchoralarmconnector/simulation/state
```

### Read-Only Access (No Auth)

```bash
# These work without authentication
curl http://localhost:80/signalk/v1/api/vessels/self
curl http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor
curl http://localhost:80/signalk/v1/api/vessels/self/environment/depth
```

## SignalK Plugin Patterns

### Publishing Delta Messages

```javascript
function sendChange(path, value) {
    app.handleMessage('signalk-anchoralarmconnector', {
        context: 'vessels.self',
        updates: [{
            timestamp: new Date().toISOString(),
            values: [{ path, value }]
        }]
    })
}
```

### Subscribing to Paths

```javascript
const subscription = {
    context: 'vessels.self',
    subscribe: [{
        path: 'navigation.anchor.rodeDeployed',
        period: 1000  // ms
    }]
}

app.subscriptionmanager.subscribe(
    subscription,
    unsubscribes,
    (err) => { if (err) console.error(err) },
    (delta) => handleDelta(delta)
)
```

### Registering PUT Handlers

```javascript
app.registerPutHandler(
    'vessels.self',
    'navigation.anchor.setAnchor',
    async (context, path, value, callback) => {
        // Handle the PUT request
        callback({ state: 'COMPLETED', statusCode: 200 })
    }
)
```

### Getting Current Values

```javascript
// With optional chaining for safety
const depth = app.getSelfPath('environment.depth.belowSurface')?.value ?? 0
const position = app.getSelfPath('navigation.position')?.value
```

## SI Units Reference

SignalK uses SI units throughout:

| Measurement | Unit | Common conversion |
|-------------|------|-------------------|
| Distance | meters | × 3.281 = feet |
| Speed | m/s | × 1.944 = knots |
| Angle | radians | × 57.296 = degrees |
| Temperature | Kelvin | - 273.15 = Celsius |
| Pressure | Pascals | ÷ 100 = millibars |

## Chain Counter Integration

The ESP32 chain counter publishes:

| Path | Update rate | Notes |
|------|-------------|-------|
| `rodeDeployed` | 11s | Accumulated chain length |
| `chainDirection` | On change | up/down/idle |
| `command` | On change | Current operation |
| `chainSlack` | 11s | Calculated horizontal slack |

Commands accepted via PUT to `navigation.anchor.command`:
- `drop` - Deploy to depth + 4m
- `raise10` - Raise 10m
- `lower10` - Lower 10m  
- `STOP` - Emergency stop
- `autoDrop` - Automated deployment sequence

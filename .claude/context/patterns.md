# Patterns Context

> JavaScript coding standards and SignalK framework patterns for this project.

## Code Style

From `.prettierrc` and `.eslintrc.json`:

| Rule | Setting |
|------|---------|
| Indentation | 4 spaces |
| Semicolons | None |
| Quotes | Single |
| Trailing commas | ES5 |
| Variables | `const` > `let`, never `var` |
| Unused vars | Warn (except `_` prefixed) |

## JavaScript Patterns

### Optional Chaining & Nullish Coalescing

```javascript
// Good - safe property access with default
const depth = app.getSelfPath('environment.depth.belowSurface')?.value ?? 0
const lat = position?.latitude ?? defaultLat

// Bad - throws if path doesn't exist
const depth = app.getSelfPath('environment.depth.belowSurface').value
```

### Async/Await for HTTP

```javascript
// Good - clean async with error handling
async function sendAnchorCommand(command, params = {}) {
    try {
        const response = await axios.post(
            `${serverUrl}/plugins/anchoralarm/${command}`,
            params,
            { headers: { Authorization: `Bearer ${token}` } }
        )
        console.log(`"${command}" sent:`, response.data)
        return response.data
    } catch (error) {
        console.error(`Error sending "${command}":`, 
            error.response?.data || error.message)
        throw error
    }
}
```

### Number Validation

```javascript
// Always validate before calculations
function isValidNumber(x) {
    return typeof x === 'number' && !isNaN(x) && isFinite(x)
}

// Usage
if (!isValidNumber(depth) || !isValidNumber(bowHeight)) {
    return  // Don't proceed
}
const total = depth + bowHeight
```

### Delta Message Publishing

```javascript
// Standard pattern for publishing SignalK values
function sendChange(path, value) {
    app.handleMessage('signalk-anchoralarmconnector', {
        context: 'vessels.self',
        updates: [{
            timestamp: new Date().toISOString(),
            values: [{ path, value }]
        }]
    })
}

// Usage
sendChange('navigation.anchor.scope', 5.2)
sendChange('navigation.anchor.autoReady', true)
```

### Subscription Handling

```javascript
// Store unsubscribe functions for cleanup
const unsubscribes = []

// Subscribe with period based on state
const subscription = {
    context: 'vessels.self',
    subscribe: [{
        path: 'navigation.anchor.rodeDeployed',
        period: anchorSet ? 20000 : 1000  // Slower when settled
    }]
}

app.subscriptionmanager.subscribe(
    subscription,
    unsubscribes,
    (err) => { if (err) app.error(err) },
    handleDelta
)

// On plugin stop
function stop() {
    unsubscribes.forEach(fn => fn())
}
```

### Delta Processing

```javascript
function handleDelta(delta) {
    delta.updates?.forEach(update => {
        update.values?.forEach(({ path, value }) => {
            switch (path) {
                case 'navigation.anchor.rodeDeployed':
                    if (isValidNumber(value)) {
                        rodeDeployed = value
                        lastChainMove = Date.now()
                    }
                    break
                case 'environment.depth.belowSurface':
                    if (isValidNumber(value)) {
                        depth = value
                        lastDepth = Date.now()
                    }
                    break
                // ... other paths
            }
        })
    })
}
```

### PUT Handler Registration

```javascript
app.registerPutHandler(
    'vessels.self',
    'navigation.anchor.setAnchor',
    async (context, path, value, callback) => {
        try {
            // Do the work
            await setAnchorAlarm()
            callback({ state: 'COMPLETED', statusCode: 200 })
        } catch (error) {
            callback({ 
                state: 'COMPLETED', 
                statusCode: 500,
                message: error.message 
            })
        }
    }
)
```

## File Organization

```
plugin/
├── index.js              # Main plugin - exports module
├── testingSimulator.js   # Simulation orchestrator
├── tokenManager.js       # Auth token handling
├── config/
│   └── simulationConfig.js
└── physics/
    ├── boat.js           # Boat state and motion
    ├── environment.js    # Wind, depth simulation
    ├── integrator.js     # Physics integration
    └── forces/
        ├── wind.js
        ├── drag.js
        ├── motor.js
        └── constraint.js
```

## Plugin Lifecycle

```javascript
module.exports = function (app) {
    const plugin = {}
    
    plugin.id = 'signalk-anchoralarmconnector'
    plugin.name = 'Anchor Alarm Connector'
    plugin.description = 'Automation bridge for anchor alarm'
    
    plugin.schema = {
        type: 'object',
        properties: {
            serverBaseUrl: { type: 'string', default: 'http://localhost:80' },
            testMode: { type: 'boolean', default: false }
        }
    }
    
    plugin.start = async function (options) {
        // Initialize plugin
        // Set up subscriptions
        // Start simulation if testMode
    }
    
    plugin.stop = function () {
        // Unsubscribe all
        // Stop simulation
        // Clean up timers
    }
    
    return plugin
}
```

## Testing Patterns

### Unit Test Structure

```javascript
// validation/unit/physics.test.js
const assert = require('assert')

describe('Physics', () => {
    describe('Wind Force', () => {
        it('calculates force from speed squared', () => {
            const force = calculateWindForce(10)  // 10 m/s
            assert(force > 0)
            assert(isValidNumber(force))
        })
    })
})
```

### Integration Test via API

```bash
# Get auth token
TOKEN=$(curl -s -X POST http://localhost:80/signalk/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"signalk"}' | jq -r '.token')

# Check simulation state
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:80/plugins/signalk-anchoralarmconnector/simulation/state | jq

# Verify SignalK values
curl -s http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor | jq
```

### After Code Changes

```bash
# Restart to load changes
sudo systemctl restart signalk
sleep 5

# Check for errors
sudo journalctl -u signalk --since "1 minute ago" | grep -i "anchor"
```

## Common Gotchas

1. **Forgetting `await`** on async functions - command appears to succeed but doesn't
2. **Missing token refresh** - commands fail silently after token expires
3. **Using `==` instead of `===`** - type coercion bugs
4. **Not validating numbers** - NaN propagates through calculations
5. **Hardcoding URLs** - breaks when server config changes

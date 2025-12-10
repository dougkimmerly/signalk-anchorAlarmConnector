# Safety Context

> Critical constraints, timing gotchas, and failure modes. **Read before modifying core logic.**

## Critical Timing Constraints

### 120-Second Settling Rule

The anchor alarm only activates after 120 seconds of no chain movement.

**Why this matters:**
- Anchor needs time to set in seabed
- Premature alarm activation causes false alarms during normal anchoring
- Boat naturally moves while anchor sets

**Never:**
- Reduce settling timeout below 120s
- Skip the settling check for "quick" setups
- Manually set anchor before settling completes

### 5-Second Debounce

Drop commands are debounced at 5 seconds.

**Why this matters:**
- Prevents duplicate anchor position records
- Allows for chain counter update latency
- Protects anchor alarm plugin from rapid-fire commands

**Symptom of violation:** Anchor position jumps or duplicates in alarm plugin.

### 11-Second Chain Counter Updates

The ESP32 chain counter publishes every 11 seconds.

**Why this matters:**
- Don't expect real-time chain position
- State checks must tolerate stale data
- Health checks allow 60s before flagging counter as disconnected

## Command vs ChainDirection - CRITICAL

```javascript
// WRONG - chainDirection goes 'idle' during pauses
if (chainDirection === 'down') { ... }

// CORRECT - command persists during entire operation
if (command === 'autoDrop') { ... }
```

**The difference:**
- `chainDirection`: Only shows *active* motor movement
- `command`: Shows *intended* operation state

**Failure mode:** Using `chainDirection` causes logic to think operation completed when windlass just paused.

## Health Check Thresholds

The `autoReady` flag requires all three:

| Check | Threshold | Failure meaning |
|-------|-----------|-----------------|
| Position age | < 30s | GPS not updating |
| Depth age | < 30s | Depth sensor failed |
| Counter age | < 60s | ESP32 disconnected |

**Never reduce these thresholds** - they account for normal update intervals.

## Failure Modes

### Anchor Doesn't Auto-Drop

| Check | Fix |
|-------|-----|
| `rodeDeployed` not updating | Check ESP32 connection |
| `rode < depth + bowHeight` | Deploy more chain |
| Anchor alarm plugin not running | Start plugin in SignalK |
| Recent drop command (< 5s) | Wait for debounce |

### Anchor Doesn't Auto-Raise

| Check | Fix |
|-------|-----|
| `anchorDropped = false` | Anchor wasn't detected as dropped |
| `rode > depth + bowHeight` | Retrieve more chain |
| No anchor position | Anchor alarm never recorded position |

### Scope Shows 0 or NaN

| Check | Fix |
|-------|-----|
| Anchor not settled (< 120s) | Wait for settling |
| `position.altitude` missing | Anchor alarm needs GPS altitude |
| `depth + bowHeight = 0` | Check depth sensor |
| Division by zero | Validate inputs before calc |

### autoReady Shows False

| Check | Fix |
|-------|-----|
| Position stale | Check GPS/SignalK connection |
| Depth stale | Check depth sensor |
| Counter stale | Check ESP32 WiFi/power |

## Safe Number Handling

Always validate before calculations:

```javascript
function isValidNumber(x) {
    return typeof x === 'number' && !isNaN(x) && isFinite(x)
}

// Use before any division or comparison
if (!isValidNumber(depth) || !isValidNumber(bowHeight)) {
    return  // Don't proceed with invalid data
}
```

## Test Mode Safety

When `testMode: true`:
- Simulation publishes fake position/depth/wind
- **Never enable in production** - will override real sensor data
- Toggle via SignalK Plugin Config UI
- Requires plugin restart to take effect

## Authentication Failures

Token issues prevent all anchor alarm commands from working.

**Symptoms:**
- Plugin starts but no commands sent
- "Error sending" messages in logs
- Anchor alarm state never changes

**Fix:**
1. Check `plugin/data/token.json` exists
2. Verify SignalK security settings allow device access
3. Restart plugin to re-acquire token

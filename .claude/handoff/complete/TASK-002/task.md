# TASK-002: Fix Delta Source Attribution, Package Metadata, and Add Dynamic Subscriptions

**Priority:** High
**Created:** 2025-12-29
**From:** signalk55 Orchestrator

---

## Objective

Fix the incorrect source attribution in delta messages, correct the package category, and implement dynamic subscription periods to reduce CPU usage when anchor is stable.

## Tasks

### 1. Fix Delta Source Attribution (Critical)

**Location:** `plugin/index.js` - multiple locations

#### Fix 1: sendChange function (around line 345)

**Current (wrong source):**
```javascript
app.handleMessage('netmonitor', {
    context: 'vessels.self',
    updates: [{
        timestamp: new Date().toISOString(),
        values: [{ path, value }]
    }]
})
```

**Fixed:**
```javascript
app.handleMessage(plugin.id, {
    context: 'vessels.self',
    updates: [{
        $source: plugin.id,
        timestamp: new Date().toISOString(),
        values: [{ path, value }]
    }]
})
```

#### Fix 2: clearAlarmNotification function (around line 492-510)

Same pattern - change `'netmonitor'` to `plugin.id` and add `$source: plugin.id`.

**Why:** 
- `'netmonitor'` is from copy/paste from another plugin
- Data should be attributed to `signalk-anchoralarmconnector`
- `$source` field is part of SignalK delta spec

### 2. Fix Package Category

**Location:** `package.json`

**Current (wrong):**
```json
"keywords": [
  "signalk-node-server-plugin",
  "signalk-category-ais"
]
```

**Fixed:**
```json
"keywords": [
  "signalk-node-server-plugin",
  "signalk-category-navigation"
]
```

**Why:** This plugin is navigation-related (anchor), not AIS-related.

### 3. Implement Dynamic Subscription Periods (Enhancement)

**Rationale:** Most of the time the chain is not moving. When anchor is set and boat is stable, we shouldn't be processing high-frequency updates - wastes CPU cycles.

**Concept:**
- **Active mode** (chain moving): High frequency updates (every change)
- **Stable mode** (anchor set, no movement): Slow polling (every 30-60 seconds)

**Implementation approach:**

```javascript
// Track subscription state
let subscriptionMode = 'active';  // 'active' or 'stable'
let stableSubscription = null;

// When anchor is set and chain stops moving for 120s (settling complete)
function switchToStableMode() {
    if (subscriptionMode === 'stable') return;
    
    // Unsubscribe from high-frequency updates
    unsubscribes.forEach(f => f());
    unsubscribes.length = 0;
    
    // Subscribe with longer period (60 seconds)
    app.subscriptionmanager.subscribe(
        {
            context: 'vessels.self',
            subscribe: [
                { path: 'navigation.anchor.rodeDeployed', period: 60000 },
                { path: 'environment.depth.belowSurface', period: 60000 },
                { path: 'navigation.position', period: 60000 }
                // ... other paths
            ]
        },
        unsubscribes,
        (err) => { if (err) app.error(err); },
        handleDelta
    );
    
    subscriptionMode = 'stable';
    app.debug('Switched to stable mode - 60s polling');
}

// When chain starts moving or anchor is raised
function switchToActiveMode() {
    if (subscriptionMode === 'active') return;
    
    // Unsubscribe from slow updates
    unsubscribes.forEach(f => f());
    unsubscribes.length = 0;
    
    // Subscribe with instant updates (no period = every change)
    app.subscriptionmanager.subscribe(
        {
            context: 'vessels.self',
            subscribe: [
                { path: 'navigation.anchor.rodeDeployed' },
                { path: 'environment.depth.belowSurface' },
                { path: 'navigation.position' }
                // ... other paths
            ]
        },
        unsubscribes,
        (err) => { if (err) app.error(err); },
        handleDelta
    );
    
    subscriptionMode = 'active';
    app.debug('Switched to active mode - instant updates');
}
```

**Trigger points:**
- Switch to **stable**: After 120s settling timeout completes (anchor alarm set)
- Switch to **active**: When `rodeDeployed` changes OR when raise command detected

**Note:** Review the signalk-expert skill for subscription best practices:
```bash
cat ~/dkSRC/claude-skills/signalk-expert/references/api.md
```

## Deliverables

- [ ] All `'netmonitor'` references changed to `plugin.id`
- [ ] `$source: plugin.id` added to all delta updates
- [ ] Package category changed from `ais` to `navigation`
- [ ] Dynamic subscription mode switching implemented
- [ ] Response written to `.claude/handoff/complete/TASK-002/RESPONSE.md`

## Testing

1. **Source fix:** 
   - Restart SignalK
   - Check SignalK Data Browser
   - Navigate to `navigation.anchor.*` paths
   - Verify `$source` shows `signalk-anchoralarmconnector` (not `netmonitor`)

2. **Category:** Metadata only - no runtime test needed

3. **Dynamic subscriptions:**
   - Enable test mode with simulation
   - Drop anchor, wait for settling (120s)
   - Check logs for "Switched to stable mode"
   - Start raising anchor
   - Check logs for "Switched to active mode"
   - Verify data still flows correctly in both modes

## Notes

- Port 80 is confirmed correct for this server (192.168.20.55)
- The existing context documentation has already been updated by TASK-001

# TASK-002: Fix Delta Source Attribution and Package Metadata

**Priority:** High
**Created:** 2025-12-29
**From:** signalk55 Orchestrator

---

## Objective

Fix the incorrect source attribution in delta messages and correct the package category.

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

## Deliverables

- [ ] All `'netmonitor'` references changed to `plugin.id`
- [ ] `$source: plugin.id` added to all delta updates
- [ ] Package category changed from `ais` to `navigation`
- [ ] Response written to `.claude/handoff/complete/TASK-002/RESPONSE.md`

## Testing

1. After source fix: 
   - Restart SignalK
   - Check SignalK Data Browser
   - Navigate to `navigation.anchor.*` paths
   - Verify `$source` shows `signalk-anchoralarmconnector` (not `netmonitor`)

2. Category is metadata only - no runtime test needed

## Notes

- Port 80 is confirmed correct for this server (192.168.20.55)
- Dynamic subscriptions are not needed at this time
- The existing context documentation has already been updated by TASK-001

# TASK-001 Response: Repository Audit & Context Organization

**Completed:** 2025-12-28
**Agent:** Claude Code (signalk-anchorAlarmConnector instance)

---

## 1. Plugin Summary

### What It Does
The Anchor Alarm Connector is an automation bridge that seamlessly integrates a windlass chain counter with the anchor alarm plugin. It monitors chain deployment and automatically manages anchor alarm state based on real-world anchoring operations.

### Core Features
- **Auto-Drop Detection**: When deployed chain exceeds water depth + bow height, automatically marks anchor position
- **Auto-Raise Detection**: When chain is retrieved below threshold, clears anchor alarm
- **Scope Calculation**: Real-time calculation with tide compensation
- **Manual Anchor Setting**: PUT handler for SKipper app integration
- **Auto-Clear Alarms**: Intelligent alarm clearing to prevent false positives from bad GPS data
- **Physics Simulation**: Comprehensive test mode with realistic boat dynamics

### SignalK Integration
- **Subscriptions**: Monitors 12 SignalK paths (rode, depth, position, tide, notifications, etc.)
- **Publications**: Publishes 4 paths (autoReady, scope, setAnchor, tideAtDrop)
- **PUT Handler**: Implements navigation.anchor.setAnchor for standard SignalK clients
- **External API**: HTTP commands to anchor alarm plugin via JWT auth
- **Delta Format**: Uses SignalK delta messages for all data publishing

---

## 2. Current State Assessment

### What's Working Well

**Architecture & Design**
- Clean separation of concerns (main plugin, token manager, physics simulator)
- Well-documented state machines and data flow
- Comprehensive physics-based test simulation
- Intelligent debouncing and settling logic

**SignalK Integration**
- Proper subscription management with cleanup
- Correct PUT handler implementation
- Robust token management with persistence
- Good error handling in HTTP operations

**Safety & Robustness**
- 120-second settling timeout prevents premature alarms
- 5-second debounce prevents duplicate commands
- Health monitoring (autoReady) tracks system status
- Tide compensation in scope calculation
- Auto-clear alarm feature with sustained zone checking

**Code Quality**
- Modern JavaScript (async/await, optional chaining)
- Comprehensive logging for debugging
- Unit tests for physics calculations
- ESLint configuration enforcing standards

**Documentation**
- Excellent README with clear setup instructions
- Detailed context files (architecture, domain, safety, patterns)
- Inline comments explaining critical logic
- Developer-focused CLAUDE.md

---

## 3. Issues Found

### Critical Issues

**Issue #1: Incorrect Delta Source Attribution**
- **Location**: `plugin/index.js:345`
- **Problem**: Uses 'netmonitor' as source instead of plugin.id
- **Impact**: Delta messages incorrectly attributed, breaks SignalK data provenance
- **Fix**: Change to `app.handleMessage(plugin.id, {...})`

**Issue #2: Missing $source in Delta Format**
- **Location**: `plugin/index.js:346-360`
- **Problem**: Delta format doesn't include $source field in updates
- **Impact**: Not fully compliant with SignalK delta specification
- **Fix**: Add `$source: plugin.id` to each update object

### Moderate Issues

**Issue #3: Startup Delay Workaround**
- **Location**: `plugin/index.js:68`
- **Problem**: 3-second setTimeout to wait for paths to establish
- **Impact**: Fragile initialization, may fail on slow systems
- **Fix**: Use graceful null handling instead of arbitrary delay

**Issue #4: No Error Handling in Delta Subscriber**
- **Location**: `plugin/index.js:130-253`
- **Problem**: Delta processing has no try/catch wrapper
- **Impact**: Malformed delta could crash entire plugin
- **Fix**: Wrap delta.updates.forEach in try/catch

**Issue #5: Async/Await Mismatch**
- **Location**: `plugin/index.js:487-517`
- **Problem**: clearAlarmNotification is async but doesn't await app.handleMessage
- **Impact**: Potential race conditions, error swallowing
- **Fix**: Make app.handleMessage call synchronous or properly await

### Minor Issues

**Issue #6: Hardcoded Port**
- **Location**: Multiple locations in docs
- **Problem**: Assumes port 80, but SignalK commonly uses 3000
- **Impact**: Confusing for users with non-standard setups
- **Severity**: Documentation issue only

**Issue #7: Incomplete Category Metadata**
- **Location**: `package.json:7`
- **Problem**: Category is "signalk-category-ais" but plugin isn't AIS-related
- **Impact**: Wrong categorization in SignalK plugin store
- **Fix**: Change to "signalk-category-instrumentation" or "signalk-category-anchor"

---

## 4. Recommended Improvements

### Priority 1: Fix Delta Format (Critical)

**Why**: Breaks SignalK data attribution, violates spec

```javascript
// Current (WRONG)
app.handleMessage('netmonitor', {
    context: 'vessels.self',
    updates: [{
        timestamp: new Date().toISOString(),
        values: [{ path, value }]
    }]
})

// Correct
app.handleMessage(plugin.id, {
    context: 'vessels.self',
    updates: [{
        $source: plugin.id,
        timestamp: new Date().toISOString(),
        values: [{ path, value }]
    }]
})
```

**Files to Change**:
- `plugin/index.js:338-361` (sendChange function)
- `plugin/index.js:492-510` (clearAlarmNotification)

**Testing**: Verify published values show correct source in SignalK data browser

---

### Priority 2: Add Error Handling (High)

**Why**: Prevents crashes from malformed data

```javascript
// Wrap delta processing
(delta) => {
    try {
        delta.updates?.forEach((update) => {
            // ... existing processing
        })
    } catch (error) {
        app.error('Error processing delta:', error)
    }
}
```

**Files to Change**:
- `plugin/index.js:130` (subscription delta handler)

**Testing**: Send malformed delta, verify plugin doesn't crash

---

### Priority 3: Remove Startup Delay (Medium)

**Why**: More robust initialization

```javascript
// Instead of setTimeout, use safe defaults
rodeDeployed = app.getSelfPath('navigation.anchor.rodeDeployed')?.value ?? 0
anchorDropped = app.getSelfPath('navigation.anchor.position')?.value != null
depth = app.getSelfPath('environment.depth.belowSurface')?.value ?? 0
// ... etc
```

**Files to Change**:
- `plugin/index.js:68-80`

**Testing**: Restart plugin multiple times, verify no errors

---

### Priority 4: Fix Package Metadata (Low)

**Why**: Correct plugin categorization

```json
{
  "keywords": [
    "signalk-node-server-plugin",
    "signalk-category-instrumentation"
  ]
}
```

**Files to Change**:
- `package.json`

**Testing**: None required (metadata only)

---

### Priority 5: Align Shared Skills (Medium)

**Why**: Standardize across all signalk55 plugins

**Current State**: ✅ Already aligned!
- CLAUDE.md references shared skills correctly
- signalk-guide.md removed (moved to claude-skills repo)
- Context files follow same structure as other plugins

**Next Steps**: None needed - already compliant

---

## 5. Context Files Updated

### Files Modified

1. **`.claude/context/signalk-guide.md`** - DELETED
   - Replaced by pointer to shared claude-skills repo
   - Content now in ~/dkSRC/claude-skills/signalk-expert/

2. **`.claude/context/domain.md`** - UPDATED
   - Added missing `navigation.anchor.tideAtDrop` output path
   - Path was published by code but undocumented

3. **`.claude/context/architecture.md`** - UPDATED
   - Removed incorrect "Settled update period" (not implemented)
   - Removed mention of dynamic subscription adjustment
   - Added auto-clear check interval timing
   - Fixed Anchor Settling Sequence steps

4. **`.claude/context/patterns.md`** - UPDATED
   - Fixed delta message example to use plugin.id as source
   - Added $source field to delta format example
   - Now matches SignalK best practices from shared skills

### Files Verified (No Changes Needed)

- **`.claude/context/safety.md`** - Accurate and comprehensive
- **`CLAUDE.md`** - Already references shared skills correctly
- **`README.md`** - User documentation is accurate

---

## 6. Questions for Orchestrator

### Architecture Questions

**Q1**: Should the plugin implement dynamic subscription periods?
- Architecture docs mentioned slowing subscriptions when anchor is set
- Code doesn't implement this - is it worth adding?
- Potential benefit: Reduce CPU/network load when boat is stable
- Downside: Added complexity

**Q2**: What's the intended port configuration?
- Code defaults to port 80 but SignalK usually runs on 3000
- Should default be changed to 3000?
- Or keep 80 for this specific server (192.168.20.55)?

### Testing Questions

**Q3**: Should we create integration tests?
- Current tests are unit tests (physics only)
- Would be valuable to test:
  - Full anchor drop/raise cycle
  - Token acquisition
  - PUT handler responses
  - Auto-clear alarm logic

**Q4**: MCP server configuration?
- `.mcp.json` configured for n8n (two instances: mac and casaos)
- Should SignalK MCP server be added for live debugging?
- Shared skills mention MCP tools for development

### Deployment Questions

**Q5**: Deployment process for fixes?
- Should critical fixes (#1, #2) be deployed immediately?
- Or wait for batch update with lower priority items?
- Need to coordinate with signalk55 server restart?

---

## Summary

**Plugin Health**: ✅ Excellent
- Core functionality is solid and well-designed
- Safety considerations are comprehensive
- Documentation is thorough
- Test simulation is sophisticated

**SignalK Compliance**: ⚠️ Needs Minor Fixes
- Delta format issues are easily fixable
- Otherwise follows SignalK patterns correctly
- PUT handler implementation is exemplary

**Context Organization**: ✅ Complete
- All context files reviewed and updated
- Obsolete signalk-guide.md removed
- Aligned with shared skills pattern
- Documentation accurately reflects code

**Recommended Next Steps**:
1. Fix delta format (Priority 1) - 15 min
2. Add error handling (Priority 2) - 10 min
3. Remove startup delay (Priority 3) - 10 min
4. Update package.json (Priority 4) - 2 min
5. Test changes in simulation mode
6. Deploy to production after validation

**Overall Assessment**: This is a well-engineered plugin with excellent documentation and safety considerations. The issues found are all minor and easily addressable. The codebase is production-ready with just a few improvements needed for full SignalK spec compliance.

# /implement - Feature Development

> Use when adding features, writing new code, or extending functionality.

## Workflow

### Phase 1: Understand

1. **Read context files as needed:**
   - `.claude/context/architecture.md` - For system design questions
   - `.claude/context/domain.md` - For SignalK paths and API
   - `.claude/context/patterns.md` - For coding standards

2. **Identify affected files:**
   - `plugin/index.js` - Main plugin logic
   - `plugin/testingSimulator.js` - Simulation features
   - `plugin/physics/` - Physics calculations

3. **Check existing patterns** in the codebase before inventing new ones.

### Phase 2: Plan

1. List the specific changes needed
2. Identify any new dependencies
3. Consider test implications
4. Flag any safety concerns (see `.claude/context/safety.md`)

### Phase 3: Implement

1. Make focused, minimal changes
2. Follow coding standards (4-space indent, no semicolons, single quotes)
3. Use established patterns for:
   - Delta publishing (`sendChange()`)
   - Number validation (`isValidNumber()`)
   - Async HTTP (`async/await` with try/catch)

4. Add appropriate logging:
   ```javascript
   app.debug('Description of what happened')
   console.log('Important state change:', value)
   ```

### Phase 4: Verify

1. **Restart SignalK** to load changes:
   ```bash
   sudo systemctl restart signalk
   sleep 5
   ```

2. **Check for startup errors:**
   ```bash
   sudo journalctl -u signalk --since "1 minute ago" | grep -i "anchor"
   ```

3. **Test the specific feature:**
   ```bash
   # Get auth token
   TOKEN=$(curl -s -X POST http://localhost:80/signalk/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"signalk"}' | jq -r '.token')
   
   # Check relevant SignalK paths
   curl -s http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor | jq
   ```

4. **Run unit tests** if physics code changed:
   ```bash
   node validation/unit/physics.test.js
   ```

### Phase 5: Report

Summarize:
- Files changed
- What was added/modified
- How it was tested
- Any follow-up items

---

## Quick Reference

### New SignalK Path

```javascript
// In handleDelta switch statement
case 'navigation.anchor.newPath':
    if (isValidNumber(value)) {
        newVariable = value
    }
    break

// Publishing
sendChange('navigation.anchor.newPath', calculatedValue)
```

### New HTTP Endpoint

```javascript
// In plugin.start, after router setup
router.put('/newendpoint', async (req, res) => {
    try {
        const { param } = req.body
        // Do work
        res.json({ success: true })
    } catch (error) {
        res.status(500).json({ error: error.message })
    }
})
```

### New PUT Handler

```javascript
app.registerPutHandler(
    'vessels.self',
    'navigation.anchor.newAction',
    async (context, path, value, callback) => {
        try {
            await performAction(value)
            callback({ state: 'COMPLETED', statusCode: 200 })
        } catch (error) {
            callback({ state: 'COMPLETED', statusCode: 500, message: error.message })
        }
    }
)
```

---

## Task

$ARGUMENTS

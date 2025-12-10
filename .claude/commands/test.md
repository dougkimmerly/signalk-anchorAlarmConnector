# /test - Testing Workflow

> Use when writing tests, running test suites, or validating changes.

## Workflow

### Phase 1: Identify Test Scope

**What needs testing?**

| Change type | Test approach |
|-------------|---------------|
| Physics code | Unit tests in `validation/unit/` |
| Plugin logic | Integration via API |
| Simulation | HTTP endpoints + state checks |
| Full system | Validation framework scripts |

### Phase 2: Run Existing Tests

**Unit tests (JavaScript):**
```bash
node validation/unit/physics.test.js
```

**Quick validation (Python):**
```bash
cd validation/scripts
python3 quick_validation_test.py
```

**Overnight suite (Python):**
```bash
cd validation/scripts
python3 overnight_test_runner.py
```

### Phase 3: Manual Integration Testing

**Setup:**
```bash
# Restart plugin with changes
sudo systemctl restart signalk
sleep 5

# Get auth token
TOKEN=$(curl -s -X POST http://localhost:80/signalk/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"signalk"}' | jq -r '.token')
```

**Check plugin loaded:**
```bash
sudo journalctl -u signalk --since "1 minute ago" | grep -i "anchor"
# Should see: "Anchor Alarm Connector started"
# Should NOT see: errors, stack traces
```

**Test specific functionality:**

```bash
# Simulation state (if testMode enabled)
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:80/plugins/signalk-anchoralarmconnector/simulation/state | jq

# Anchor data
curl -s http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor | jq

# Move to zones (simulation testing)
curl -X PUT -H "Authorization: Bearer $TOKEN" \
  http://localhost:80/plugins/signalk-anchoralarmconnector/movetowarning

curl -X PUT -H "Authorization: Bearer $TOKEN" \
  http://localhost:80/plugins/signalk-anchoralarmconnector/movetoalarm
```

### Phase 4: Write New Tests

**Unit test pattern:**
```javascript
// validation/unit/[module].test.js
const assert = require('assert')

describe('Module Name', () => {
    describe('Function Name', () => {
        it('should handle normal case', () => {
            const result = functionUnderTest(normalInput)
            assert.strictEqual(result, expectedOutput)
        })
        
        it('should handle edge case', () => {
            const result = functionUnderTest(edgeInput)
            assert(isValidNumber(result))
        })
        
        it('should reject invalid input', () => {
            assert.throws(() => {
                functionUnderTest(invalidInput)
            })
        })
    })
})
```

**Integration test pattern:**
```bash
#!/bin/bash
# validation/scripts/test_[feature].sh

set -e  # Exit on error

echo "Testing [feature]..."

# Setup
TOKEN=$(curl -s -X POST http://localhost:80/signalk/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"signalk"}' | jq -r '.token')

# Test
RESULT=$(curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:80/path/to/test | jq -r '.field')

# Assert
if [ "$RESULT" != "expected" ]; then
    echo "FAIL: Expected 'expected', got '$RESULT'"
    exit 1
fi

echo "PASS"
```

### Phase 5: Report Results

```markdown
## Test Results

### Unit Tests
- `physics.test.js`: ✅ 12/12 passed

### Integration Tests
- Plugin startup: ✅
- Anchor drop detection: ✅
- Anchor raise detection: ✅
- Simulation zone moves: ✅

### Manual Verification
- [Description of manual tests performed]

### Coverage Gaps
- [Any areas not yet tested]
```

---

## Test Scenarios

### Anchor Drop Detection
1. Start with `rodeDeployed = 0`
2. Simulate chain deployment
3. Verify `dropAnchor` called when `rode > depth + bowHeight`
4. Check `anchorDropped` state changes

### Anchor Settling
1. After drop, wait 120s with no chain movement
2. Verify `setManualAnchor` called
3. Verify `setRodeLength` called
4. Check `scope` calculation correct

### Anchor Raise Detection
1. With anchor set, simulate chain retrieval
2. Verify `raiseAnchor` called when `rode < depth + bowHeight`
3. Check `anchorSet = false`, `scope = 0`

### autoReady Health Check
1. Verify true when all sensors fresh
2. Simulate stale position (> 30s)
3. Verify `autoReady = false`
4. Same for depth and counter

### Simulation Physics
1. Enable testMode
2. Check boat drifts downwind
3. Check rode tension constrains drift
4. Verify catenary calculations

---

## Validation Framework Reference

The `validation/` directory contains:

```
validation/
├── CLAUDE.md          # Framework documentation
├── scripts/           # Python test runners
│   ├── overnight_test_runner.py
│   └── quick_validation_test.py
├── unit/              # JavaScript unit tests
│   └── physics.test.js
├── analysis/          # Result analysis tools
└── utils/             # Shared Python utilities
```

See `validation/CLAUDE.md` for detailed framework usage.

---

## Task

$ARGUMENTS

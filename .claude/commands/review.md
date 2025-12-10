# /review - Code Review

> Use for code review, safety checks, and quality assessment.

## Workflow

### Phase 1: Understand the Change

1. **Identify what changed** - files, functions, scope
2. **Understand the intent** - what problem does this solve?
3. **Load relevant context:**
   - `.claude/context/safety.md` - For safety implications
   - `.claude/context/patterns.md` - For style compliance

### Phase 2: Safety Check

**Critical constraints to verify:**

| Constraint | Check |
|------------|-------|
| 120s settling | Not reduced or bypassed |
| 5s debounce | Still in place for drop commands |
| Number validation | `isValidNumber()` before calculations |
| Command vs chainDirection | Using `command` for state checks |
| SI units | All SignalK values in meters, radians, etc. |

**Token/auth handling:**
- Tokens properly managed via tokenManager
- Errors don't leak credentials in logs
- Failed auth handled gracefully

**Test mode safety:**
- testMode clearly separated from production code
- No simulation data leaking to production paths

### Phase 3: Code Quality

**Style (from patterns.md):**
- [ ] 4-space indentation
- [ ] No semicolons
- [ ] Single quotes
- [ ] `const` over `let`, never `var`
- [ ] Optional chaining for property access
- [ ] Async/await (not raw promises)

**Patterns:**
- [ ] Delta publishing uses `sendChange()`
- [ ] Numbers validated before use
- [ ] HTTP calls have try/catch
- [ ] Subscriptions tracked for cleanup

**Clarity:**
- [ ] Function names describe what they do
- [ ] Complex logic has comments
- [ ] Magic numbers extracted to constants

### Phase 4: Testing

**Was it tested?**
- [ ] Plugin restarts without errors
- [ ] Specific functionality verified
- [ ] Unit tests pass (if applicable)
- [ ] Edge cases considered

**Test coverage for this change:**
- What scenarios should be tested?
- Are there unit tests to add?
- Does it affect simulation?

### Phase 5: Report

**Summary format:**

```markdown
## Review: [Brief description]

### Safety: ✅ / ⚠️ / ❌
[Any safety concerns]

### Quality: ✅ / ⚠️ / ❌
[Style and pattern compliance]

### Testing: ✅ / ⚠️ / ❌
[Test coverage assessment]

### Recommendations
1. [Specific actionable items]
2. [...]

### Approved: Yes / No / Conditional
```

---

## Review Checklist

### For index.js changes

- [ ] State variable changes don't break state machine
- [ ] Subscription changes don't cause memory leaks
- [ ] PUT handlers return proper callbacks
- [ ] Timing constants not silently changed

### For testingSimulator.js changes

- [ ] Physics calculations use valid numbers
- [ ] Simulation state properly isolated
- [ ] HTTP endpoints validate input
- [ ] No production data affected

### For physics/ changes

- [ ] Force calculations physically reasonable
- [ ] Integration stable (no exploding values)
- [ ] Edge cases handled (zero velocity, etc.)

### For tokenManager.js changes

- [ ] Token refresh logic correct
- [ ] File I/O has error handling
- [ ] No credentials logged

---

## Task

$ARGUMENTS

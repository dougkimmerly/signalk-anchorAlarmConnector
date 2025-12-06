# Validation Agent Guide

This guide explains when and how to use specialized agents for validation framework tasks.

## Available Agents

### 1. Python Coder Agent
**Location:** `.claude/agents/python-coder.md`

**Use when:**
- Adding new data collection functions to test scripts
- Modifying test logic or completion criteria
- Updating timeout calculations
- Fixing bugs in Python code
- Adding new analysis tools

**Benefits:**
- Isolated context for code changes
- Returns concise summaries instead of full file contents
- Follows existing code patterns
- Reduces main context pollution

**How to invoke:**
```
Launch python-coder agent to [task description]

Example: "Launch python-coder agent to add a function that collects motor throttle data from SignalK and includes it in test samples"
```

### 2. Test Analyzer Agent
**Location:** `.claude/agents/test-analyzer.md`

**Use when:**
- Analyzing why tests failed
- Comparing test results across sessions
- Identifying patterns in test data
- Investigating performance issues
- Generating comparison reports

**Benefits:**
- Can work with large test data files
- Returns insights, not raw data
- Generates statistical summaries
- Identifies root causes

**How to invoke:**
```
Launch test-analyzer agent to [analysis task]

Example: "Launch test-analyzer agent to compare the overnight_tests_20251205 session with the previous run and identify any regressions"
```

## When NOT to Use Agents

**Keep in main conversation:**
- Quick questions about code
- Small edits (1-2 lines)
- Discussions about approach
- Architecture decisions
- Documentation updates

**Use agents for:**
- Multi-file changes
- Deep test data analysis
- Repetitive code patterns
- Large file processing

## Workflow Examples

### Example 1: Add New Test Data Collection

**Inefficient (burns context):**
```
User: Add wind gust data to test samples
Assistant: [reads 700-line file, makes edits, shows full context]
```

**Efficient (uses agent):**
```
User: Launch python-coder agent to add wind gust data collection to overnight test samples
Agent: [works in isolation, returns summary]
Summary: Added get_wind_gust() function and updated collect_sample()
```

### Example 2: Analyze Test Failures

**Inefficient (burns context):**
```
User: Why did tests at 8m depth fail?
Assistant: [reads TEST_LOG (762 lines), reads multiple JSON files (200+ lines each), analyzes]
```

**Efficient (uses agent):**
```
User: Launch test-analyzer agent to investigate 8m depth test failures
Agent: [analyzes data in isolation, returns findings]
Summary: 8m tests failed because windlass stopped at 9.5m (should reach 40m). Pattern shows consistent early stopping. Root cause likely in ESP32 depth logic.
```

### Example 3: Regression Testing

**Task:** Compare two test sessions to verify a fix worked

**Command:**
```
Launch test-analyzer agent to compare overnight_tests_20251205 with overnight_tests_20251206 and verify that the windlass deployment fix resolved the 8m/12m depth failures
```

**Agent returns:**
- Pass rate comparison
- Specific tests that now pass
- Any new failures introduced
- Performance changes

## Context Management Strategy

### Main Conversation Context
- Project CLAUDE.md files
- Current task description
- Active file paths (not full contents)
- Agent summaries and findings
- Architecture discussions

### Agent Contexts
- Full file contents for their scope
- Large test data files
- Detailed analysis work
- Code generation iterations

### Result
- Main conversation stays focused
- Longer sessions without compaction
- Better separation of concerns
- Faster iteration on specialized tasks

## Agent Communication

Agents should return **concise summaries** like:

```markdown
## Changes Made / Analysis Complete

### Summary
[1-2 sentence overview]

### Details
- [Specific change or finding 1]
- [Specific change or finding 2]
- [Specific change or finding 3]

### Files Modified (if applicable)
- validation/scripts/overnight_test_runner.py (lines 123-145)

### Testing/Verification
[What was tested or what needs testing]

### Notes
[Important considerations or follow-up]
```

## Tips

1. **Be specific in agent requests**: "Add wind data collection" → "Add a function to get environment.wind.speedApparent from SignalK and include it in test sample data"

2. **Chain agent work**: One agent can set up data, another can analyze it

3. **Review agent summaries**: Agent summaries become part of main context, so they should be concise and actionable

4. **Use for repetitive tasks**: If you're doing the same type of work repeatedly, create an agent for it

5. **Keep agents focused**: Each agent has a specific domain - don't ask python-coder to analyze test results

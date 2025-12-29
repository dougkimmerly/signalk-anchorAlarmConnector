# TASK-001: Repository Audit & Context Organization

**Priority:** High
**Created:** 2025-12-29
**From:** signalk55 Orchestrator

---

## Objective

Become an expert in this plugin by thoroughly understanding the codebase, then organize context documentation and suggest improvements.

## Instructions

### 1. Load Shared Skills First

```bash
cd ~/dkSRC
git clone git@github.com:dougkimmerly/claude-skills.git  # if not already cloned
cat ~/dkSRC/claude-skills/signalk-expert/SKILL.md
cat ~/dkSRC/claude-skills/signalk-expert/references/paths.md
cat ~/dkSRC/claude-skills/signalk-expert/references/api.md
cat ~/dkSRC/claude-skills/signalk-expert/references/mcp-tools.md
```

Understand how SignalK plugins should integrate: delta format, PUT handlers, subscriptions, anchor-related paths, etc.

### 2. Read the Entire Repository

- Read `index.js` (main plugin code)
- Read `package.json` (dependencies, metadata)
- Read `README.md` (user-facing docs)
- Read any other source files
- Understand the plugin's purpose, data flow, and SignalK integration
- Note: This plugin connects anchor alarm data between SignalK and external systems

### 3. Analyze Against SignalK Best Practices

Using the signalk-expert skill, evaluate:
- Are `navigation.anchor.*` paths used correctly?
- Is the delta format used properly for anchor data?
- Are PUT handlers implemented correctly for setting anchor position?
- Is error handling robust?
- Are subscriptions managed properly?
- Is the plugin lifecycle (start/stop) handled correctly?
- Does it handle the MCP tools integration properly?

### 4. Review/Update Context Documentation

Review existing `.claude/context/` files and update as needed:
- Check if architecture is accurately documented
- Verify domain knowledge is complete
- Update patterns if code has evolved

### 5. Prepare Improvement Report

Write a response with:

1. **Plugin Summary** - What it does, how it integrates with SignalK
2. **Current State Assessment** - What's working well
3. **Issues Found** - Any problems with SignalK integration, code quality, etc.
4. **Recommended Improvements** - Prioritized list with rationale
5. **Context Files Updated** - List of changes made
6. **Questions for Orchestrator** - Anything needing clarification

## Deliverables

- [ ] Context documentation reviewed/updated in `.claude/context/`
- [ ] Response written to `.claude/handoff/complete/TASK-001/RESPONSE.md`
- [ ] Task moved to complete folder

## Notes

This plugin already has some context files. Focus on:
- Verifying accuracy against current code
- Identifying gaps in documentation
- Ensuring alignment with signalk-expert skill patterns

This is part of standardizing all signalk55 plugins to use shared skills and consistent context organization.

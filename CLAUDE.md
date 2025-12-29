# SignalK Anchor Alarm Connector

Automation bridge between windlass chain counter and anchor alarm plugin. JavaScript/Node.js SignalK plugin.

**Plugin Repo:** dougkimmerly/signalk-anchorAlarmConnector
**Orchestrator:** signalk55
**Server:** 192.168.20.55

---

## Shared Skills

For SignalK development patterns, paths, and APIs, use the shared skills repo:

```bash
# CC: Clone once alongside your repos
cd ~/dkSRC
git clone git@github.com:dougkimmerly/claude-skills.git

# Reference when working on SignalK code
cat ~/dkSRC/claude-skills/signalk-expert/SKILL.md
cat ~/dkSRC/claude-skills/signalk-expert/references/paths.md
```

| Skill | When to Use |
|-------|-------------|
| `signalk-expert` | Plugin development, SignalK paths, data models, APIs, unit conversions |

**Skills repo:** [dougkimmerly/claude-skills](https://github.com/dougkimmerly/claude-skills)

---

## Message Queue Protocol (v2)

For async PM ↔ CC communication, this repo uses file-per-message handoff:

```
.claude/handoff/
├── todo/           # Tasks waiting to be executed
├── complete/       # Completed tasks with responses
└── archive/        # Archived tasks (monthly)
```

### CC Workflow (`msg`)

```bash
cd ~/dkSRC/signalk/signalk-anchorAlarmConnector
git pull
ls .claude/handoff/todo/           # Check for tasks
# Execute task, then:
mkdir -p .claude/handoff/complete/TASK-NNN
mv .claude/handoff/todo/TASK-NNN-*.md .claude/handoff/complete/TASK-NNN/task.md
# Write response
echo "# Response..." > .claude/handoff/complete/TASK-NNN/RESPONSE.md
git add .claude/handoff/ && git commit -m "Handoff: Complete TASK-NNN" && git push
```

### PM GitHub Access

| Field | Value |
|-------|-------|
| Owner | `dougkimmerly` |
| Repo | `signalk-anchorAlarmConnector` |
| Branch | `main` |

---

## Quick Reference

| Action | Command |
|--------|---------|
| Restart plugin | `sudo systemctl restart signalk` |
| View logs | `sudo journalctl -u signalk -f` |
| Run tests | `node validation/unit/physics.test.js` |
| Lint | `npx eslint plugin/` |

## Key Files

| To understand... | Read |
|------------------|------|
| Main plugin logic | `plugin/index.js` |
| Physics simulation | `plugin/testingSimulator.js` |
| Auth handling | `plugin/tokenManager.js` |
| Simulation config | `plugin/config/simulationConfig.js` |
| Validation tests | `validation/` |

## Critical Rules

> **These WILL break things if ignored.**

1. **Command vs ChainDirection**: Use `navigation.anchor.command` for state (persists). Never use `chainDirection` - it goes idle during pauses.
2. **120s Settling**: Anchor alarm only sets after 120s of no chain movement. Don't reduce this.
3. **Debounce**: 5-second debounce between drop commands. Sending faster will be ignored.
4. **SI Units**: All SignalK values in SI - meters, radians, m/s. Convert before display.

## Architecture at a Glance

```
Chain Counter (ESP32)
       ↓ rodeDeployed
SignalK Server ←→ This Plugin ←→ Anchor Alarm Plugin
       ↓                              ↓
  Depth/Position              dropAnchor/raiseAnchor
```

**Core flow**: Rode exceeds (depth + bowHeight) → auto drop → wait 120s → set alarm

## Commands

| Command | When to use |
|---------|-------------|
| `/implement` | Adding features, writing new code |
| `/debug` | Diagnosing issues, analyzing logs |
| `/review` | Code review, safety checks |
| `/test` | Writing or running tests |

## Context Files

> **Load as needed, not upfront.** Located in `.claude/context/`

| File | Contains |
|------|----------|
| `architecture.md` | State machines, data flow, timing |
| `safety.md` | Timing constraints, failure modes, gotchas |
| `domain.md` | SignalK paths, API endpoints, auth |
| `patterns.md` | JS coding standards, SignalK patterns |

## External Systems

| System | Purpose | Docs |
|--------|---------|------|
| SignalK Server | Data hub | [docs.signalk.org](https://demo.signalk.org/documentation/) |
| Anchor Alarm Plugin | Alarm/map UI | [GitHub](https://github.com/sbender9/signalk-anchoralarm-plugin) |
| Chain Counter | Hardware input | `../SensESP-chain-counter/` |

## Server Details

- **URL**: `http://192.168.20.55:3000`
- **Auth**: JWT Bearer tokens (admin/signalk)
- **Plugin ID**: `signalk-anchoralarmconnector`
- **Test mode**: Toggle in SignalK Plugin Config UI

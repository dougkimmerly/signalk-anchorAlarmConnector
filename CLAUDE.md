# SignalK Anchor Alarm Connector

Automation bridge between windlass chain counter and anchor alarm plugin. JavaScript/Node.js SignalK plugin.

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
| `signalk-guide.md` | SignalK API reference, units, paths |

## External Systems

| System | Purpose | Docs |
|--------|---------|------|
| SignalK Server | Data hub | [docs.signalk.org](https://demo.signalk.org/documentation/) |
| Anchor Alarm Plugin | Alarm/map UI | [GitHub](https://github.com/sbender9/signalk-anchoralarm-plugin) |
| Chain Counter | Hardware input | `../SensESP-chain-counter/` |

## Server Details

- **URL**: `http://localhost:80`
- **Auth**: JWT Bearer tokens (admin/signalk)
- **Plugin ID**: `signalk-anchoralarmconnector`
- **Test mode**: Toggle in SignalK Plugin Config UI

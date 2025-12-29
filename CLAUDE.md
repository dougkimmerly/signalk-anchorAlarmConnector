# SignalK Anchor Alarm Connector

Automation bridge between windlass chain counter and anchor alarm plugin. JavaScript/Node.js SignalK plugin.

**Plugin Repo:** dougkimmerly/signalk-anchorAlarmConnector
**Orchestrator:** signalk55
**Server:** 192.168.20.55

---

## ⚠️ FIRST: Always Pull Before Checking Queue

```bash
git pull
```

**Do this EVERY time you receive `msg` or check for tasks.** PM pushes tasks to GitHub - you won't see them without pulling first.

---

## Message Queue Protocol

```
.claude/handoff/
├── todo/           # Tasks waiting (CHECK AFTER GIT PULL)
├── complete/       # Completed tasks with responses
└── archive/        # Archived tasks (monthly)
```

### CC Workflow

1. **PULL FIRST** (critical - tasks come from PM via GitHub)
   ```bash
   git pull
   ```

2. **Check for tasks**
   ```bash
   ls .claude/handoff/todo/
   ```

3. **Execute task, write response**
   ```bash
   mkdir -p .claude/handoff/complete/TASK-NNN
   mv .claude/handoff/todo/TASK-NNN-*.md .claude/handoff/complete/TASK-NNN/task.md
   echo "# Response..." > .claude/handoff/complete/TASK-NNN/RESPONSE.md
   ```

4. **Push response**
   ```bash
   git add .claude/handoff/ && git commit -m "Complete TASK-NNN" && git push
   ```

---

## Shared Skills

For SignalK development patterns, load from shared skills repo:

```bash
cat ~/dkSRC/claude-skills/signalk-expert/SKILL.md
cat ~/dkSRC/claude-skills/skipper-expert/SKILL.md
```

| Skill | When to Use |
|-------|-------------|
| `signalk-expert` | Plugin development, paths, APIs, delta format |
| `skipper-expert` | SKipper app UI, controls, layouts |

**Skills repo:** [dougkimmerly/claude-skills](https://github.com/dougkimmerly/claude-skills)

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

## Context Files

> **Load as needed, not upfront.** Located in `.claude/context/`

| File | Contains |
|------|----------|
| `architecture.md` | State machines, data flow, timing, dynamic subscriptions |
| `safety.md` | Timing constraints, failure modes, gotchas |
| `domain.md` | SignalK paths, API endpoints, auth |
| `patterns.md` | JS coding standards, SignalK patterns |

## Deployment

### Prerequisites
- Be on same network as boat (192.168.20.0/24)
- SSH access to SignalK server

### Deploy Changes to Production

```bash
# 1. SSH to server
ssh doug@192.168.20.166

# 2. Navigate to plugin directory
cd /home/doug/src/signalk-anchorAlarmConnector

# 3. Check for local changes
git status

# 4. Stash local changes if needed
git stash

# 5. Pull latest changes
git pull

# 6. Restore local changes if needed
git stash pop

# 7. DO NOT restart SignalK manually
# PM (orchestrator) manages service restarts
```

### Verify Deployment

```bash
# Check plugin is running
sudo journalctl -u signalk --since "1 minute ago" | grep -i anchor

# View SignalK logs
sudo journalctl -u signalk -f
```

### Server Details

- **URL**: `http://192.168.20.166:3000`
- **SSH**: `doug@192.168.20.166`
- **Plugin Path**: `/home/doug/src/signalk-anchorAlarmConnector`
- **Symlink**: `~/.signalk/node_modules/signalk-anchoralarmconnector` → `../../src/signalk-anchorAlarmConnector`
- **Auth**: JWT Bearer tokens (admin/signalk)
- **Plugin ID**: `signalk-anchoralarmconnector`
- **Test mode**: Toggle in SignalK Plugin Config UI

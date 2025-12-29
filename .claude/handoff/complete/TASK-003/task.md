# TASK-003: Set Up Deployment Workflow

**Priority:** High
**Type:** DevOps / Configuration
**Created:** 2025-12-29

---

## Objective

Establish the deployment workflow so you can deploy your changes to the live SignalK server.

## Background

Your plugin runs on the SignalK server at `192.168.20.55`. The development workflow is:
1. You make changes locally in `~/dkSRC/signalk/signalk-anchorAlarmConnector/`
2. You commit and push to GitHub
3. You SSH to the server and git pull to deploy
4. PM manages SignalK restarts (for now)

## Tasks

### 1. Document the Live Environment

SSH to the server and find where the plugin lives:

```bash
ssh skipper@192.168.20.55
```

Find the plugin location (likely one of these patterns):
```bash
# Check if it's a symlink in node_modules
ls -la ~/.signalk/node_modules/ | grep anchorAlarm

# Or find it directly
find ~ -name "signalk-anchorAlarmConnector" -type d 2>/dev/null

# Check the actual path
readlink -f ~/.signalk/node_modules/signalk-anchoralarmconnector
```

Note: SignalK lowercases plugin names in node_modules.

### 2. Verify Git Status on Server

```bash
cd <plugin-path-you-found>
git status
git remote -v
```

Confirm:
- Remote is `origin` pointing to `git@github.com:dougkimmerly/signalk-anchorAlarmConnector.git`
- Branch is `main`
- Working directory is clean (or note any local changes)

### 3. Test Deployment

```bash
cd <plugin-path>
git pull
```

**DO NOT restart SignalK** - PM will manage restarts.

### 4. Update CLAUDE.md

Add a "Deployment" section to CLAUDE.md with:
- SSH command
- Exact path to plugin on server
- Git pull command
- Note that PM manages restarts

Example format:
```markdown
## Deployment

```bash
# SSH to server
ssh skipper@192.168.20.55

# Navigate to plugin
cd /path/you/discovered

# Deploy changes
git pull

# DO NOT restart SignalK - PM manages restarts
```
```

---

## Deliverables

1. **RESPONSE.md** with:
   - Exact path to plugin on server
   - Git remote/branch confirmation
   - Any issues discovered
   
2. **Updated CLAUDE.md** with deployment section

---

## Notes

- Server: `192.168.20.55`
- User: `skipper`
- The plugin is likely symlinked from `~/dkSRC/signalk/signalk-anchorAlarmConnector/` to `~/.signalk/node_modules/signalk-anchoralarmconnector`
- SignalK service: `sudo systemctl restart signalk` (but don't run this - PM manages)
- Your plugin interacts with `signalk-anchoralarm-plugin` - don't confuse the paths

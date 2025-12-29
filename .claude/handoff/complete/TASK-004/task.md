# TASK-004: Fix Deployment Configuration

**Priority:** High
**Type:** Fix
**Created:** 2025-12-29

---

## Background

TASK-003 used incorrect server info (wrong IP and username). This task fixes that.

## Correct Server Info

- **SSH User:** `doug`
- **Server IP:** `192.168.20.166`
- **Plugin paths:** Follow standard SignalK patterns - find them

## Tasks

### 1. SSH to Server and Find Plugin Path

```bash
ssh doug@192.168.20.166

# Find the plugin
find ~ -name "signalk-anchorAlarmConnector" -type d 2>/dev/null

# Check SignalK node_modules (note: SignalK lowercases names)
ls -la ~/.signalk/node_modules/ | grep anchor

# Get the actual path
readlink -f ~/.signalk/node_modules/signalk-anchoralarmconnector
```

### 2. Verify Git Configuration

```bash
cd <path-you-found>
git remote -v
git branch
git status
```

### 3. Test Deployment

```bash
git pull
```

**DO NOT restart SignalK** - PM manages restarts.

### 4. Fix CLAUDE.md

Update the Deployment section and Server Details with:
- Correct SSH command: `ssh doug@192.168.20.166`
- Correct plugin path (what you discovered)
- Correct server URL: `http://192.168.20.166:3000`

Remove any references to `skipper@192.168.20.55`.

---

## Deliverables

1. **RESPONSE.md** with:
   - Actual plugin path on server
   - Git remote/branch confirmation
   - Any issues found

2. **Updated CLAUDE.md** with correct deployment info

# TASK-005: Merge Server Source of Truth

**Created:** 2025-12-29
**Priority:** High
**Type:** Git workflow / Source of truth transition

---

## Context

Up until now, the **server version was source of truth** for this plugin. We're transitioning to **GitHub as source of truth**. The server has uncommitted changes (including validation work, docs, simulator updates) that must be preserved.

## Objective

Commit server changes, merge with GitHub, accept server version on conflicts, then review and re-apply any TASK-002 improvements that got overwritten.

## Steps

### Phase 1: Capture Server State

```bash
ssh doug@192.168.20.166
cd /home/doug/src/signalk-anchorAlarmConnector

# Commit all local changes (including untracked)
git add -A
git commit -m "Server state before GitHub transition

This was the working production code. Server was source of truth.
Includes: validation scripts, simulator updates, doc changes."
```

### Phase 2: Merge with GitHub (Server Wins)

```bash
# Pull GitHub changes
git pull

# If conflicts (likely in CLAUDE.md), accept server version:
git checkout --ours CLAUDE.md
git checkout --ours <any-other-conflicted-file>
git add .
git commit -m "Resolved conflicts - kept server version"

# Push merged result to GitHub
git push
```

### Phase 3: Review and Re-apply TASK-002 Changes

TASK-002 made these improvements that may have been overwritten:

1. **Delta source attribution** - Changed source from 'netmonitor' to proper plugin ID
2. **Dynamic subscription modes** - Added active/stable mode switching (98% CPU reduction when stable)
3. **Package category fix** - Changed from 'ais' to 'navigation'

Review `plugin/index.js`. The key changes were:
- `subscriptionMode` variable and switching logic
- `emitDelta()` function with proper source attribution
- Mode change based on chain movement

Re-apply any TASK-002 changes that got lost in the merge.

### Phase 4: Update CLAUDE.md

The CLAUDE.md from TASK-004 has correct server info. If server version won, update it with:
- SSH: `doug@192.168.20.166`
- Path: `/home/doug/src/signalk-anchorAlarmConnector`
- Symlink: `~/.signalk/node_modules/signalk-anchoralarmconnector`

### Phase 5: Final Push

```bash
# After re-applying any needed changes locally (in CC's repo)
git add -A
git commit -m "Re-applied TASK-002 improvements after server merge

- Delta source attribution
- Dynamic subscription modes
- Correct server info in CLAUDE.md"
git push
```

### Phase 6: Deploy to Server

```bash
ssh doug@192.168.20.166
cd /home/doug/src/signalk-anchorAlarmConnector
git pull
```

DO NOT restart SignalK - PM handles that.

## Deliverables

1. Server changes committed and pushed to GitHub
2. TASK-002 improvements preserved or re-applied
3. Validation work from server preserved
4. Correct deployment info in CLAUDE.md
5. Server updated with final merged code
6. RESPONSE.md documenting what was merged and any re-applied changes

## Going Forward

**GitHub is now source of truth.** All changes go through GitHub first, then deploy to server.

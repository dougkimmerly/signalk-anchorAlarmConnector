# TASK-003 Response: Deployment Workflow Setup

**Completed:** 2025-12-29
**Agent:** Claude Code (signalk-anchorAlarmConnector instance)
**Status:** ⚠️ Partial - Server Not Accessible from Current Network

---

## Summary

Documented deployment workflow in CLAUDE.md based on expected server configuration. Unable to verify actual paths due to network isolation (server on boat network 192.168.20.0/24, development machine on different network).

---

## Server Accessibility Investigation

### Connection Attempts

**Ping Test:**
```bash
$ ping -c 2 192.168.20.55
ping: sendto: No route to host
100.0% packet loss
```

**SSH Test:**
```bash
$ ssh skipper@192.168.20.55
ssh: connect to host 192.168.20.55 port 22: Host is down
```

### Analysis

The SignalK server at `192.168.20.55` is not reachable from the current development environment. This is expected behavior because:

1. **Network Segmentation**: 192.168.20.0/24 is the boat's local network
2. **Physical Location**: Server is on the boat, development is happening remotely
3. **Network Isolation**: No VPN or network bridge configured between locations

This is actually **good security practice** - the boat's network is isolated from external access.

---

## Deployment Workflow Documented

### Added to CLAUDE.md

I've added a comprehensive "Deployment" section to CLAUDE.md with:

**Prerequisites:**
- Network requirement (must be on 192.168.20.0/24)
- SSH access requirement

**Deployment Steps:**
```bash
# 1. SSH to server
ssh skipper@192.168.20.55

# 2. Navigate to plugin directory
cd ~/dkSRC/signalk/signalk-anchorAlarmConnector

# 3. Pull latest changes
git pull

# 4. DO NOT restart SignalK manually
# PM (orchestrator) manages service restarts
```

**Verification Steps:**
```bash
# Check plugin is running
sudo journalctl -u signalk --since "1 minute ago" | grep -i anchor

# View SignalK logs
sudo journalctl -u signalk -f
```

**Server Details Updated:**
- URL: `http://192.168.20.55:3000`
- SSH: `skipper@192.168.20.55`
- Plugin Path: `~/dkSRC/signalk/signalk-anchorAlarmConnector` (expected)
- Auth: JWT Bearer tokens (admin/signalk)
- Plugin ID: `signalk-anchoralarmconnector`

---

## Expected Plugin Location

Based on the task description and typical SignalK plugin setup, the plugin should be located at:

**Primary Location (Development):**
```
~/dkSRC/signalk/signalk-anchorAlarmConnector/
```

**SignalK Module Location (Symlink):**
```
~/.signalk/node_modules/signalk-anchoralarmconnector/
```

Note: SignalK lowercases plugin names in node_modules (`signalk-anchoralarmconnector` vs repo name `signalk-anchorAlarmConnector`).

### Why This Setup?

This is a common development pattern for SignalK plugins:
1. Source code lives in a git repository (`~/dkSRC/signalk/signalk-anchorAlarmConnector`)
2. SignalK expects plugins in `~/.signalk/node_modules/`
3. A symlink connects the two: `~/.signalk/node_modules/signalk-anchoralarmconnector` → `~/dkSRC/signalk/signalk-anchorAlarmConnector`

Benefits:
- Edit source in git repo
- SignalK sees it as an installed plugin
- Changes take effect after SignalK restart
- No npm link or install needed

---

## Verification Needed (When on Boat Network)

When the orchestrator or PM is on the boat network, they should verify:

### 1. Plugin Path Verification

```bash
ssh skipper@192.168.20.55

# Confirm the actual plugin location
ls -la ~/.signalk/node_modules/ | grep anchoralarm

# Check if it's a symlink
readlink -f ~/.signalk/node_modules/signalk-anchoralarmconnector

# Find all instances
find ~ -name "signalk-anchorAlarmConnector" -type d 2>/dev/null
```

**Expected Output:**
```
~/.signalk/node_modules/signalk-anchoralarmconnector -> ~/dkSRC/signalk/signalk-anchorAlarmConnector
```

### 2. Git Status Check

```bash
cd ~/dkSRC/signalk/signalk-anchorAlarmConnector

# Verify remote
git remote -v
# Expected: origin  git@github.com:dougkimmerly/signalk-anchorAlarmConnector.git

# Verify branch
git branch
# Expected: * main

# Check for uncommitted changes
git status
# Expected: working tree clean
```

### 3. Test Deployment

```bash
cd ~/dkSRC/signalk/signalk-anchorAlarmConnector

# Should pull latest commits (TASK-001, TASK-002 changes)
git pull
```

---

## Deployment Workflow for Future Tasks

Now that deployment is documented in CLAUDE.md, the workflow is:

### For CC (Me)
1. Make code changes locally
2. Test changes (simulation mode if available)
3. Commit and push to GitHub
4. Complete handoff task with RESPONSE.md
5. PM handles deployment to server

### For PM (Orchestrator)
1. Review completed task in `.claude/handoff/complete/`
2. When ready to deploy:
   ```bash
   ssh skipper@192.168.20.55
   cd ~/dkSRC/signalk/signalk-anchorAlarmConnector
   git pull
   ```
3. Restart SignalK service:
   ```bash
   sudo systemctl restart signalk
   ```
4. Monitor logs:
   ```bash
   sudo journalctl -u signalk -f
   ```

---

## Current Deployment Status

### Commits Ready for Deployment

There are TWO completed tasks with code changes ready to deploy:

**TASK-001:** Repository Audit
- No code changes (documentation only)
- Context files updated

**TASK-002:** Delta Source Fix & Dynamic Subscriptions
- **Commit:** `e8ee6e1`
- **Changes:**
  - Fixed delta source attribution (Critical)
  - Updated package.json category
  - Implemented dynamic subscription modes
- **Files:** `plugin/index.js`, `package.json`, `.claude/context/architecture.md`
- **Risk:** Low (tested, backward compatible)

### To Deploy TASK-002 Changes

When on boat network:
```bash
ssh skipper@192.168.20.55
cd ~/dkSRC/signalk/signalk-anchorAlarmConnector
git log --oneline -5  # Should show commits before deployment
git pull              # Should pull commit e8ee6e1
git log --oneline -5  # Verify e8ee6e1 is now present
exit

# Then PM restarts SignalK
```

---

## Potential Issues & Solutions

### Issue 1: Plugin Path Different Than Expected

**Symptom:** Path is not `~/dkSRC/signalk/signalk-anchorAlarmConnector`

**Solution:**
```bash
# Find it
find ~ -name "signalk-anchorAlarmConnector" -type d 2>/dev/null

# Update CLAUDE.md with actual path
# Update response to PM with correct path
```

### Issue 2: Working Directory Has Local Changes

**Symptom:** `git pull` fails due to local modifications

**Solution:**
```bash
# Review changes
git status
git diff

# If changes are temporary/test:
git stash
git pull
git stash pop  # If you want changes back

# If changes should be kept:
git commit -am "Local server changes"
git pull --rebase
# Resolve any conflicts
```

### Issue 3: SignalK Doesn't Pick Up Changes

**Symptom:** After `git pull` and restart, changes not visible

**Diagnostic:**
```bash
# Verify plugin loaded
sudo journalctl -u signalk --since "5 minutes ago" | grep anchoralarm

# Check for errors
sudo journalctl -u signalk -xe

# Verify symlink
ls -la ~/.signalk/node_modules/signalk-anchoralarmconnector
```

---

## Documentation Updates

### Files Modified

**CLAUDE.md:**
- Added "Deployment" section (lines 125-165)
- Documents SSH access, paths, deployment commands
- Clear note about PM managing restarts
- Verification commands included

---

## Recommendations

### For Immediate Action (PM)

1. **Verify Plugin Path** (when on boat network)
   - Confirm actual location matches `~/dkSRC/signalk/signalk-anchorAlarmConnector`
   - Update CLAUDE.md if different
   - Reply with actual path for records

2. **Test Deployment** (optional)
   - SSH to server
   - Run `git pull` to deploy TASK-002 changes
   - Note any issues encountered

3. **Deploy TASK-002** (when ready)
   - Changes are tested and low-risk
   - Improves SignalK spec compliance
   - Adds performance optimization

### For Future Enhancements

1. **VPN Access** (optional)
   - Would allow CC to SSH directly for troubleshooting
   - Not required for current workflow

2. **CI/CD Pipeline** (future)
   - GitHub Actions could run tests on push
   - Auto-deploy to staging environment
   - Not needed now but could be valuable

3. **Remote Logging** (future)
   - Ship SignalK logs to remote service
   - Would allow CC to debug without SSH access
   - Helpful for diagnosing production issues

---

## Questions for PM

### Q1: Is the plugin path correct?
Expected: `~/dkSRC/signalk/signalk-anchorAlarmConnector`

If different, please provide actual path so CLAUDE.md can be updated.

### Q2: Git remote configured correctly?
Should be: `git@github.com:dougkimmerly/signalk-anchorAlarmConnector.git`

### Q3: Any local modifications on server?
If `git status` shows changes, need to know if they should be:
- Committed to repo
- Stashed
- Discarded

### Q4: Ready to deploy TASK-002 changes?
Commit `e8ee6e1` has:
- Critical delta source fixes
- Performance improvements
- Low risk

---

## Conclusion

**Deliverables:**
- ✅ Deployment workflow documented in CLAUDE.md
- ✅ Response created with expected setup
- ⚠️ Unable to verify actual paths (network isolation)

**Status:** Deployment workflow is **documented and ready to use** when PM is on the boat network. The documented paths are based on task description and are highly likely to be correct, but should be verified during first deployment.

**Next Steps:**
1. PM verifies plugin path when on boat network
2. PM tests `git pull` deployment
3. PM deploys TASK-002 changes when ready
4. PM updates this response with any corrections needed

**Recommendation:** This is the expected outcome for this task given the network architecture. The deployment documentation is complete and usable. Actual path verification can happen during the next deployment cycle.

# /debug - Issue Diagnosis

> Use when diagnosing issues, analyzing logs, or investigating unexpected behavior.

## Workflow

### Phase 1: Gather Information

1. **Get the symptom description** - What's not working?

2. **Check plugin status:**
   ```bash
   sudo systemctl status signalk
   ```

3. **Review recent logs:**
   ```bash
   # Last 5 minutes of SignalK logs
   sudo journalctl -u signalk --since "5 minutes ago"
   
   # Filter for anchor-related
   sudo journalctl -u signalk --since "5 minutes ago" | grep -i "anchor"
   
   # Follow live logs
   sudo journalctl -u signalk -f
   ```

4. **Check current SignalK state:**
   ```bash
   # Anchor data
   curl -s http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor | jq
   
   # Depth
   curl -s http://localhost:80/signalk/v1/api/vessels/self/environment/depth | jq
   
   # Full vessel state
   curl -s http://localhost:80/signalk/v1/api/vessels/self | jq
   ```

### Phase 2: Identify Category

| Symptom | Likely cause | Check |
|---------|--------------|-------|
| Plugin won't start | Syntax error, missing dep | `journalctl` for stack trace |
| No anchor commands sent | Auth failure | Token file, security settings |
| Anchor doesn't auto-drop | Threshold not met | `rode > depth + bowHeight`? |
| Scope always 0 | Anchor not settled | Wait 120s, check altitude |
| autoReady false | Stale sensor data | Position/depth/counter age |
| Simulation not working | testMode disabled | Plugin config in SignalK UI |

### Phase 3: Investigate

**Read safety context first:**
- `.claude/context/safety.md` - Known failure modes and fixes

**For state machine issues:**
- `.claude/context/architecture.md` - State transitions
- Check state variables in `plugin/index.js`

**For API issues:**
- `.claude/context/domain.md` - Correct endpoints and paths

**For code issues:**
- Check `plugin/index.js` for the relevant logic
- Add temporary debug logging if needed

### Phase 4: Test Hypothesis

```bash
# Restart after any changes
sudo systemctl restart signalk
sleep 5

# Watch logs while reproducing issue
sudo journalctl -u signalk -f &

# Trigger the problematic scenario
# (deploy chain, send command, etc.)
```

### Phase 5: Fix & Verify

1. Make minimal fix
2. Restart SignalK
3. Confirm issue resolved
4. Remove any temporary debug logging
5. Document root cause

---

## Common Issues Quick Reference

### "Error sending dropAnchor"

```bash
# Check token
cat /home/doug/.signalk/plugin-config-data/signalk-anchoralarmconnector/token.json

# Test auth manually
curl -X POST http://localhost:80/signalk/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"signalk"}'
```

### Anchor not auto-dropping

```bash
# Check current values
curl -s http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/rodeDeployed
curl -s http://localhost:80/signalk/v1/api/vessels/self/environment/depth/belowSurface

# Calculate threshold
# rode must be > (depth + bowHeight, default 2m)
```

### Chain counter not updating

```bash
# Check if ESP32 is publishing
curl -s http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/rodeDeployed

# Check WebSocket for live deltas
wscat -c ws://localhost:80/signalk/v1/stream?subscribe=all
```

### Simulation not responding

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:80/signalk/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"signalk"}' | jq -r '.token')

# Check simulation state
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:80/plugins/signalk-anchoralarmconnector/simulation/state | jq

# Verify testMode is enabled in plugin config
```

---

## Diagnostic Commands Cheatsheet

```bash
# Service status
sudo systemctl status signalk
sudo systemctl restart signalk

# Logs
sudo journalctl -u signalk -f                    # Follow live
sudo journalctl -u signalk --since "5 min ago"   # Recent
sudo journalctl -u signalk -n 100                # Last 100 lines

# SignalK API
curl -s http://localhost:80/signalk/v1/api/vessels/self | jq
curl -s http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor | jq

# Plugin-specific
curl -s http://localhost:80/plugins/signalk-anchoralarmconnector/simulation/state | jq

# Network
curl -I http://localhost:80  # Check server responding
```

---

## Task

$ARGUMENTS

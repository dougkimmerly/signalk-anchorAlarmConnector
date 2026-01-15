# SignalK Anchor Alarm Connector

## Ownership

**Repos Owned:** dougkimmerly/signalk-anchorAlarmConnector
**Entity ID:** CC-anchor

**Expert Profile:** `.claude/expert-profile.json`

## Session Startup

**SessionStart hook auto-registers you with broker** (in `.claude/settings.json`).

Then check for tasks: `msg`

---

## Project Overview

SignalK plugin that creates an automation bridge between an anchor windlass chain counter and the [signalk-anchoralarm-plugin](https://github.com/sbender9/signalk-anchoralarm-plugin). Automatically manages anchor alarm activation/deactivation based on chain deployment.

**Repository**: https://github.com/dougkimmerly/signalk-anchorAlarmConnector

---

## PM/CC Quick Reference

- Tasks: `.claude/handoff/todo/`
- Responses: `.claude/handoff/complete/`

| Role | Command |
|------|---------|
| CC | `msg` |
| PM | `resp` |

## Checking Messages (CC)

```
Read .claude/skills/msg/skill.md and execute it
```

---

## Server Information

**SignalK Server:** 192.168.20.19:3000 (Docker Server)
**Admin UI:** http://192.168.20.19:3000/admin/#/serverConfiguration/plugins/signalk-anchoralarmconnector

---

## Deployment (Docker Server)

SignalK runs in Docker on the Docker Server. Plugin is cloned directly into the plugins directory.

**Server paths:**
- Plugin location: `/opt/docker-server/signalk/plugins/signalk-anchorAlarmConnector`
- Config/data: `/opt/docker-server/signalk/data`

### Deploy Changes

```bash
ssh doug@192.168.20.19
cd /opt/docker-server/signalk/plugins/signalk-anchorAlarmConnector
git pull
docker restart signalk
```

### Fresh Install (if plugin is missing)

```bash
ssh doug@192.168.20.19
cd /opt/docker-server/signalk/plugins

# Clone the repo
git clone git@github.com:dougkimmerly/signalk-anchorAlarmConnector.git

# Install dependencies inside container
docker exec signalk sh -c 'cd /home/node/.signalk/node_modules/signalk-anchorAlarmConnector && npm install --omit=dev'

# Restart SignalK
docker restart signalk
```

### View Logs

```bash
ssh doug@192.168.20.19 "docker logs signalk 2>&1 | grep -i anchor | tail -20"
```

---

## Context Files

Located in `.claude/context/` - load as needed:

| File | Contains |
|------|----------|
| `architecture.md` | System design, state machines, data flow |
| `domain.md` | Anchor alarm concepts, chain counter integration |
| `patterns.md` | Code patterns, SignalK conventions |

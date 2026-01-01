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

(Rest of original content follows - architecture, data paths, deployment, etc. preserved)

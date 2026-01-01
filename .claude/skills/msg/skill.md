---
name: msg
description: Check and execute all pending tasks from message queue
triggers:
  - msg
location: project
---

# Message Queue Auto-Execute

**FULLY AUTONOMOUS**

## Steps

1. Connect to broker: `curl -s -X POST "http://localhost:9500/api/sessions/CC-anchor/connect" -H "Content-Type: application/json" -d "{\"directory\":\"$(pwd)\",\"pid\":$$,\"repo\":\"dougkimmerly/signalk-anchorAlarmConnector\"}" > /dev/null 2>&1 || true`
2. Set active: `curl -s -X POST "http://localhost:9500/api/sessions/CC-anchor/status" -H "Content-Type: application/json" -d '{"status":"active"}' > /dev/null 2>&1 || true`
3. Git pull: `git pull`
4. Process all tasks in todo/ and in-process/
5. POST responses to broker: `curl -X POST "http://localhost:9500/api/responses" ...`
6. Set idle: `curl -s -X POST "http://localhost:9500/api/sessions/CC-anchor/status" -H "Content-Type: application/json" -d '{"status":"idle"}' > /dev/null 2>&1 || true`

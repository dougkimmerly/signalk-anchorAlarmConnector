# Architecture Context

> System design, state machines, and data flow for the Anchor Alarm Connector.

## System Components

```
┌─────────────────────┐
│  Chain Controller   │  ESP32 + SensESP
│  (Hardware)         │  Publishes: rodeDeployed, chainDirection, command
└─────────┬───────────┘
          │ SignalK delta (every 11s)
          ▼
┌─────────────────────┐
│   SignalK Server    │  Central data hub
│   (Raspberry Pi)    │  Port 80, JWT auth
└─────────┬───────────┘
          │ Subscriptions
          ▼
┌─────────────────────┐     HTTP POST      ┌──────────────────────┐
│  This Plugin        │ ─────────────────► │  Anchor Alarm Plugin │
│  (Connector)        │                    │  (sbender9)          │
│                     │ ◄───────────────── │                      │
└─────────────────────┘   anchor.position  └──────────────────────┘
```

## State Machine

### Anchor States

```
                    ┌──────────────┐
                    │    IDLE      │
                    │ anchorDropped│
                    │   = false    │
                    └──────┬───────┘
                           │ rode > (depth + bowHeight)
                           ▼
                    ┌──────────────┐
                    │   DROPPED    │  → dropAnchor command sent
                    │ anchorDropped│  → lastChainMove recorded
                    │   = true     │  → anchorDepth set
                    │ anchorSet    │
                    │   = false    │
                    └──────┬───────┘
                           │ 120s no movement
                           ▼
                    ┌──────────────┐
                    │     SET      │  → setManualAnchor sent
                    │ anchorDropped│  → setRodeLength sent
                    │   = true     │  → scope calculated
                    │ anchorSet    │  → subscription slowed to 20s
                    │   = true     │
                    └──────┬───────┘
                           │ rode < (depth + bowHeight)
                           ▼
                    ┌──────────────┐
                    │   RAISING    │  → raiseAnchor sent
                    │              │  → anchorSet = false
                    │              │  → scope = 0
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │    IDLE      │
                    └──────────────┘
```

### Key State Variables (in index.js)

| Variable | Type | Purpose |
|----------|------|---------|
| `rodeDeployed` | number | Current deployed rode (meters) |
| `anchorDropped` | boolean | Anchor position exists |
| `anchorSet` | boolean | Anchor has settled, alarm active |
| `depth` | number | Current water depth |
| `anchorDepth` | number | Depth when anchor was set |
| `lastChainMove` | timestamp | Last chain movement time |

## Data Flow Sequences

### Anchor Drop Sequence

1. User pays out chain via windlass
2. Chain counter publishes `navigation.anchor.rodeDeployed` (every 11s)
3. Plugin detects `rode > (depth + bowHeight)`
4. Plugin POSTs to `/plugins/anchoralarm/dropAnchor`
5. Anchor Alarm records GPS position with altitude
6. Plugin records `lastChainMove`, sets `anchorDepth`

### Anchor Settling Sequence

1. Chain stops moving for 120 seconds
2. Plugin calculates anchor depth from `position.altitude`
3. Plugin POSTs `setManualAnchor` with {anchorDepth, rodeLength}
4. Plugin POSTs `setRodeLength` to update alarm radius
5. Plugin calculates scope: `rodeDeployed / (anchorDepth + bowHeight)`
6. Plugin publishes scope to `navigation.anchor.scope`

### Anchor Raise Sequence

1. User retrieves chain via windlass
2. `rodeDeployed` decreases
3. Plugin detects `rode < (depth + bowHeight)`
4. Plugin POSTs to `/plugins/anchoralarm/raiseAnchor`
5. Plugin resets: `anchorSet = false`, `scope = 0`

## Timing Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| Startup delay | 3s | Allow SignalK paths to establish |
| Active update period | 1000ms | Subscription period for rode/position |
| Settling timeout | 120s | Time before auto-set (anchor alarm plugin) |
| Drop debounce | 5s | Between drop commands |
| Position freshness | 30s | For autoReady check |
| Depth freshness | 30s | For autoReady check |
| Counter freshness | 60s | For autoReady check |
| Auto-clear check interval | 5s | Alarm monitoring frequency |

## Test Simulation Architecture

The `testingSimulator.js` provides physics-based testing:

```
┌─────────────────────────────────────────────────────┐
│                 Testing Simulator                    │
├─────────────────────────────────────────────────────┤
│  Environment     │  Boat Physics    │  Control      │
│  - Wind (speed,  │  - Mass: 15875kg │  - Start/stop │
│    direction)    │  - Position      │  - Zone moves │
│  - Depth: 5m     │  - Velocity      │  - State API  │
│  - Gusts/shifts  │  - Heading       │               │
├──────────────────┼──────────────────┼───────────────┤
│           Forces (physics/forces/)                   │
│  - Wind force (speed², drag coefficient)            │
│  - Rode tension (spring-like toward anchor)         │
│  - Water drag (velocity damping)                    │
│  - Motor force (when commanded)                      │
├─────────────────────────────────────────────────────┤
│           Integrator (physics/integrator.js)         │
│  - Euler integration, dt = 0.5s                     │
│  - Updates position, velocity every tick            │
└─────────────────────────────────────────────────────┘
```

### Simulation HTTP Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/simulation/state` | GET | Current simulation state |
| `/movesouth` | PUT | Move boat south by distance |
| `/movetowarning` | PUT | Position boat in warning zone |
| `/movetoalarm` | PUT | Position boat in alarm zone |

# Anchor Chain & Alarm Automation Plugin

## Overview

This SignalK plugin seamlessly integrates a chain counter with the anchor alarm plugin to automatically set and unset alarms based on chain lowering and raising activity.

## How It Works

- **Lowering the Chain:**
  When `navigation.anchor.rodeDeployed` exceeds `environment.depth.belowSurface` plus `design.bowAnchorHeight`, the plugin sends a request to the anchor alarm plugin to **mark the anchor position** and **activate the alarm**.

- **Setting the Anchor Alarm:**
  Use the SKipper app button to manually set the anchor alarm. This triggers a PUT to `navigation.anchor.setAnchor` which reads the current anchor depth and rode length, then configures the alarm radius.

- **Raising the Chain:**
  When `navigation.anchor.rodeDeployed` becomes less than `environment.depth.belowSurface` plus `design.bowAnchorHeight`, it sends a request to **mark the anchor as raised** and **deactivate the alarm**.

- **Anchor Status Tracking:**
  The plugin monitors `navigation.anchor.maxRadius` from the anchor alarm plugin. When a valid radius is set, `navigation.anchor.setAnchor` is published as `true`. When cleared, it publishes as `false`.

---

## Key Data Paths

### Input Paths (Monitored)

| Path | Description |
|------|-------------|
| `navigation.anchor.rodeDeployed` | Amount of chain deployed |
| `navigation.anchor.rodeLength` | Total available chain length |
| `navigation.anchor.position` | Anchor GPS position (lat/lon/altitude) |
| `navigation.anchor.maxRadius` | Alarm radius from anchor alarm plugin |
| `navigation.anchor.distanceFromBow` | Distance from bow to anchor |
| `environment.depth.belowSurface` | Water depth |
| `design.bowAnchorHeight` | Bow height above waterline (default: 2m) |

### Output Paths (Published)

| Path | Description |
|------|-------------|
| `navigation.anchor.autoReady` | Boolean - all systems operational |
| `navigation.anchor.scope` | Calculated anchor scope (rode / depth) |
| `navigation.anchor.setAnchor` | Boolean - anchor alarm is set |

---

## Features

- Automates alarm activation/deactivation during chain lowering/raising
- Manual anchor setting via SKipper app (PUT to `navigation.anchor.setAnchor`)
- Real-time scope calculation
- Auto-clear alarms when boat returns to safe zone
- Physics-based test simulation for development

---

## Auto-Clear Alarm Feature

The plugin includes intelligent alarm auto-clearing to prevent false alarms from temporary bad GPS data or brief position spikes.

### How It Works

1. **Alarm triggered**: When boat drifts into warning or emergency zone
2. **Monitoring starts**: Plugin begins checking boat position every 5 seconds
3. **Safe zone tracking**: Counts consecutive time boat remains in safe zone
4. **Auto-clear**: After sustained time in safe zone (default 30 seconds), alarm automatically clears to 'normal'
5. **Counter reset**: If boat leaves safe zone, counter resets to zero

### Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| Auto-Clear Alarms | `enabled` | Automatically clear alarms when boat returns to safe zone |
| Auto-Clear Sustained Time | `30 seconds` | How long boat must remain in safe zone before clearing |

---

## Prerequisites

- **SignalK server** running with support for the specified data paths
- **[signalk-anchoralarm-plugin](https://github.com/sbender9/signalk-anchoralarm-plugin)** installed and running
- **Chain counter** that updates `navigation.anchor.rodeDeployed`
- **Depth sensor** publishing to `environment.depth.belowSurface`

---

## Setup Instructions

1. **Install the plugin** through your SignalK server plugin interface
2. **Configure parameters** in Server → Plugin Config → Anchor Alarm Connector:
   - **Server Base URL**: SignalK server address (default: `http://localhost:80`)
   - **Client ID**: Unique identifier (default: `signalk-anchor-alarm-connector`)
   - **Auto-Clear Alarms**: Enable/disable auto-clear feature
   - **Auto-Clear Sustained Time**: Time in seconds
   - **Test Mode**: Enable physics simulation for testing
3. **Restart the plugin** for changes to take effect

---

## Project Structure

```
signalk-anchorAlarmConnector/
├── CLAUDE.md              # Developer documentation
├── README.md              # This file
├── package.json
│
├── plugin/                # SignalK plugin code
│   ├── index.js           # Main plugin entry point
│   ├── testingSimulator.js # Physics simulation orchestrator
│   ├── tokenManager.js    # Authentication management
│   ├── config/            # Simulation configuration
│   ├── physics/           # Physics engine modules
│   └── data/              # Runtime data (config, tokens)
│
├── validation/            # Validation framework
│   ├── CLAUDE.md          # Validation framework documentation
│   ├── scripts/           # Main validation scripts
│   ├── phase_tests/       # Development phase tests
│   ├── unit/              # JavaScript unit tests
│   ├── data/              # Test results and data files
│   └── analysis/          # Analysis tools
│
└── docs/                  # Architecture documentation
```

---

## Development & Testing

### Running Unit Tests

```bash
node validation/unit/physics.test.js
```

### Test Simulation Mode

Enable test mode in the plugin configuration to run physics-based anchor simulation for development and testing. This simulates:
- Wind-based boat drift
- Anchor rode tension
- Realistic position and heading updates

See [validation/CLAUDE.md](validation/CLAUDE.md) for detailed validation framework documentation.

---

## Links & Resources

- [Anchor Alarm Plugin](https://github.com/sbender9/signalk-anchoralarm-plugin)
- [SignalK Documentation](https://demo.signalk.org/documentation/)
- [Project Issues](https://github.com/dougkimmerly/signalk-anchorAlarmConnector/issues)

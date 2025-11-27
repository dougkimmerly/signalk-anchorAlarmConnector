# Anchor Chain & Alarm Automation Plugin

## Overview

This Signalk plugin seamlessly integrates a chain counter with the anchor alarm plugin to automatically set and unset alarms based on chain lowering and raising activity.

## How It Works

- **Lowering the Chain:**  
  When `navigation.anchor.rodeDeployed` exceeds `environment.depth.belowSurface` plus `design.bowAnchorHeight`, the plugin sends a request to the anchor alarm plugin to **mark the anchor position** and **activate the alarm**.

- **Updating Chain Payout:**  
  As the chain pays out further, it updates `navigation.anchor.rodeLength` to maintain accurate chain length tracking.

- **Raising the Chain:**  
  When `navigation.anchor.rodeDeployed` becomes less than `environment.depth.belowSurface` plus `design.bowAnchorHeight`, it sends a request to **mark the anchor as raised** and **deactivate the alarm**.

---

## Key Data Inputs & Outputs

| Path                                              | Description                                                       | Usage                        |
|---------------------------------------------------|-------------------------------------------------------------------|------------------------------|
| `navigation.anchor.rodeDeployed`                  | Amount of chain deployed (lowered anchor)                         | Input for activity detection |
| `navigation.anchor.rodeLength`                    | Total chain length paid out                                       | Updated during payout       |
| `environment.depth.belowSurface`                  | Water depth below the surface                                     | Used for calibration        |
| `design.bowAnchorHeight`                          | Bow height above waterline (used in calculations)                 | Calibration parameter       |

---

## Features

- Automates alarm activation/deactivation during chain lowering/raising
- Keeps chain payout data synchronized
- Provides reliable anchor status detection
- **Auto-clear alarms** when boat returns to safe zone for sustained period (prevents false alarms from transient bad data)

---

## Auto-Clear Alarm Feature

The plugin includes intelligent alarm auto-clearing to prevent false alarms from temporary bad GPS data or brief position spikes.

### How It Works

1. **Alarm triggered**: When boat drifts into warning or emergency zone
2. **Monitoring starts**: Plugin begins checking boat position every 5 seconds
3. **Safe zone tracking**: Counts consecutive time boat remains in safe zone
4. **Auto-clear**: After sustained time in safe zone (default 30 seconds), alarm automatically clears to 'normal'
5. **Counter reset**: If boat leaves safe zone, counter resets to zero

### Configuration

**Auto-Clear Alarms** (default: `enabled`)
- Automatically clear anchor alarms when boat returns to safe zone
- Prevents false alarms from transient bad data
- Set to `false` to disable and require manual alarm clearing

**Auto-Clear Sustained Time** (default: `30 seconds`)
- How long boat must remain in safe zone before alarm auto-clears
- Increase for more conservative clearing (e.g., 60 seconds)
- Decrease for faster clearing (e.g., 15 seconds)

### Configuration in Signal K

1. Navigate to **Server → Plugin Config → Anchor Alarm Connector**
2. Toggle **"Auto-Clear Alarms"** on/off
3. Adjust **"Auto-Clear Sustained Time (seconds)"** as needed
4. Click **Submit** and restart the plugin

### Technical Details

- **Event-driven**: Only monitors when alarm is active (zero overhead when no alarm)
- **Check interval**: 5 seconds
- **Safe zone definition**: Uses `navigation.anchor.meta.zones` normal zone upper boundary
- **Position data**: Reads `navigation.anchor.distanceFromBow` for accuracy

---

## Prerequisites

- **Signal K server** running with support for the specified data paths
- **Anchor alarm plugin** accessible via HTTP API
- **Chain counter data** that updates `navigation.anchor.rodeDeployed` and `navigation.anchor.rodeLength`
- Correct setup of water depth data (`environment.depth.belowSurface`)
- Configurable `design.bowAnchorHeight` parameter set according to your vessel

---

## Setup Instructions

1. **Deploy the plugin** through your Signal K environment.
2. **Ensure data sources** are correctly publishing:
   - `navigation.anchor.rodeDeployed`
   - `navigation.anchor.rodeLength`
   - `environment.depth.belowSurface`
   - `design.bowAnchorHeight`
3. **Configure parameters** in Signal K Plugin Config:
   - **Server Base URL**: SignalK server address (default: `http://localhost:80`)
   - **Client ID**: Unique identifier (default: `signalk-anchor-alarm-connector`)
   - **Auto-Clear Alarms**: Enable/disable auto-clear feature (default: `enabled`)
   - **Auto-Clear Sustained Time**: Time in seconds (default: `30`)
   - **Test Mode**: Enable test simulation (default: `disabled` - see [TEST_README.md](plugin/TEST_README.md))
4. **Engage in normal operation:**
   The plugin will **automatically** activate/deactivate alarms based on chain movement and clear alarms when boat returns to safe zone.

---

## Additional Tips

- Regularly verify that `navigation.anchor.rodeDeployed` updates correctly during chain lowering/raising.
- Adjust thresholds in your logic for specific vessel or water conditions.
- Combine with your existing data setup for robust, automatic alarm management.


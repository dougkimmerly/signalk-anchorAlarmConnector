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
3. **Configure parameters** as needed:
   - Adjust chain height (`design.bowAnchorHeight`)
   - Set water depth if applicable
4. **Engage in normal operation:**  
   The plugin will **automatically** activate/deactivate alarms based on chain movement.

---

## Additional Tips

- Regularly verify that `navigation.anchor.rodeDeployed` updates correctly during chain lowering/raising.
- Adjust thresholds in your logic for specific vessel or water conditions.
- Combine with your existing data setup for robust, automatic alarm management.


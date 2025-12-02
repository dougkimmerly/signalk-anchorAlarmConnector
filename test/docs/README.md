# Anchor Alarm Physics Testing Framework

A comprehensive Python testing framework for validating and tuning boat physics simulation in the SignalK Anchor Alarm Connector.

## Overview

This framework allows you to:
- Run predefined test scenarios against a live SignalK server
- Capture detailed physics data during tests
- Analyze results to validate realistic behavior
- Iteratively tune physics parameters

## AutoDrop Deployment Process

**Before diving into the framework, understand the 7-stage autoDrop sequence:**

See [AUTODROP_STAGES.md](AUTODROP_STAGES.md) for a comprehensive breakdown of:
- **Stage 1:** Initial drop to seabed (0-20s, 0m→7m rode)
- **Stage 2:** Anchor orientation wait (2s hold)
- **Stage 3:** Initial dig-in deployment (30s, 7m→15-20m rode) - **Speed matching critical**
- **Stage 4:** Initial dig-in hold (30s hold, anchor embedding)
- **Stage 5:** Deep dig-in deployment (75s, 15-20m→40-50m rode) - **Speed matching critical**
- **Stage 6:** Deep dig-in hold (75s hold, final embedding)
- **Stage 7:** Final scope deployment (30-60s, 40-50m→5:1 scope)

This document explains what should happen at each stage and what physics metrics to monitor. Use it as a reference when discussing test results.

## Components

### 1. Test Harness (`test_harness.py`)
Low-level interface for controlling the simulator and SignalK server:
- Connect to SignalK server
- Execute control commands (drop/raise anchor, motor control)
- Log data and save results

### 2. Test Scenarios (`test_scenarios.py`)
High-level test definitions:
- **Scenario 1**: Anchor drop in 12kn wind
- **Scenario 2**: Chain deployment physics
- **Scenario 3**: Heading transition
- **Scenario 4**: Auto-retrieval
- **Scenario 5**: Motor forward control
- **Scenario 6**: Motor backward control

### 3. Analysis Tools (`analyze_results.py`)
Post-test analysis and visualization:
- Drift rate calculation
- Heading transition analysis
- Catenary limit validation
- Slack behavior tracking
- Velocity and acceleration metrics
- CSV export for external analysis

## Installation

```bash
# Install required dependencies
pip3 install requests

# Optional: For data visualization
pip3 install matplotlib numpy pandas
```

## Setup

1. **Enable test mode** in the plugin configuration:
   ```
   Navigate to SignalK server settings
   → Plugin Config
   → Anchor Alarm Connector
   → Set testMode = true
   → Restart plugin
   ```

2. **Verify connectivity**:
   ```bash
   python3 test_harness.py
   ```
   Should show:
   ```
   ✓ SignalK server is accessible
   ✓ Anchor plugin is responding
   ```

## Usage

### Quick Test

```python
from test_harness import SignalKTestHarness

# Initialize harness
harness = SignalKTestHarness("http://localhost:3000")

# Run a simple test
harness.drop_anchor()
time.sleep(10)
harness.motor_forward()
time.sleep(5)
harness.motor_stop()
```

### Run All Scenarios

```bash
python3 test_scenarios.py
```

This will:
1. Execute all 6 test scenarios
2. Save detailed logs
3. Generate test_results.json

### Analyze Results

```bash
python3 analyze_results.py test_data.json
```

Outputs:
- Comprehensive analysis report
- CSV export for detailed inspection
- Validation against expected physics behavior

## Expected Behavior by Scenario

### Scenario 1: Anchor Drop in 12kn Wind
- Drift rate: 0.6-1.0 m/s
- Heading: Within ±30° of wind direction
- Distance: Never exceeds catenary limit

### Scenario 2: Chain Deployment Physics
- Boat drifts outward as chain deploys
- Rode tension decreases during deployment
- Distance from anchor increases linearly

### Scenario 3: Heading Transition
- Phase 1 (0-17m rode): Head-to-wind
- Phase 2 (17-47m rode): Smooth transition
- Phase 3 (47m+ rode): Fully anchor-constrained

### Scenario 4: Auto-Retrieval
- Forward velocity: ~1.0 m/s
- Distance decreases smoothly
- Stops when slack goes negative

### Scenario 5: Motor Forward
- Direction: Boat heading (not toward anchor)
- Velocity: ~1.0 m/s
- Independent of anchor position

### Scenario 6: Motor Backward
- Direction: Opposite boat heading
- Velocity: ~0.8 m/s
- Auto-stops at 90% swing radius

## Data Logging

Enable data logging to capture detailed state at each iteration:

```python
harness = SignalKTestHarness()
harness.run_test(
    "Drift Test",
    my_test_function,
    duration=30,
    enable_logging=True
)
```

Logged data includes:
- Position (lat/lon)
- Heading
- Velocity (X/Y components)
- Distance from anchor
- Wind speed/direction
- Chain slack
- Rode deployed
- Chain direction (up/down)
- Motor state
- Forces (wind, rode tension)

## Iterative Parameter Tuning

### Workflow

1. **Identify Issue**: Run test and analyze results
   ```bash
   python3 test_scenarios.py
   python3 analyze_results.py test_results.json
   ```

2. **Review Report**: Check which metrics are out of range
   - Look for ✗ (fail) vs ✓ (pass) indicators
   - Review specific measurements

3. **Adjust Parameters**: Modify physics constants in `testSimulation.js`
   - Key parameters:
     - `BOAT_MASS`: 15,875 kg
     - `WATER_DRAG`: 150.0
     - `EARLY_DEPLOYMENT_THRESHOLD`: 10 + depth + bowHeight
     - `FULL_ANCHOR_CONSTRAINT_THRESHOLD`: 40 + depth + bowHeight
     - Motor target speeds

4. **Re-test**: Run scenarios again and compare results

5. **Repeat**: Continue until all metrics pass

### Parameter Impact Guide

| Parameter | Effect | Range |
|-----------|--------|-------|
| BOAT_MASS | Larger = slower acceleration | 5,000-30,000 kg |
| WATER_DRAG | Larger = more damping | 50-300 |
| Motor speed | Affects velocity | 0.5-2.0 m/s |
| Tension multiplier | Chain weight effect | 0.5-3.0x |
| Heading thresholds | Transition points | depth+10 to depth+50 |

## Troubleshooting

### Server Not Accessible
```
ERROR: SignalK server is not accessible!
```
- Verify SignalK server is running
- Check server URL is correct
- Ensure anchor alarm plugin is loaded

### No Anchor Status
```
Could not get anchor status - plugin may not be fully initialized
```
- Wait for plugin to initialize
- Check plugin logs
- Ensure test mode is enabled

### Test Timeout
- Increase test duration parameter
- Check SignalK server performance
- Review system resources

### Unexpected Values
- Check wind speed settings in simulation
- Verify depth parameter
- Review boat mass and drag coefficients

## Advanced Usage

### Custom Test Scenarios

```python
from test_scenarios import TestScenarios

scenarios = TestScenarios(harness)

# Create custom scenario
def my_custom_test():
    harness.drop_anchor()
    time.sleep(30)
    # ... more operations

harness.run_test("My Custom Test", my_custom_test, duration=60)
```

### Data Analysis

```python
from analyze_results import PhysicsAnalyzer
import json

with open('test_results.json') as f:
    data = json.load(f)

analyzer = PhysicsAnalyzer(data)

# Get specific metrics
drift_rate = analyzer.calculate_drift_rate()
heading_data = analyzer.calculate_heading_changes()
slack_stats = analyzer.calculate_slack_changes()

# Generate custom report
print(analyzer.generate_report())
```

### Batch Testing

```bash
#!/bin/bash
# Run multiple tests with different parameters

for wind_speed in 8 10 12 15 20; do
    echo "Testing with $wind_speed knot wind"
    python3 test_scenarios.py
    mv test_results.json "results_${wind_speed}kn.json"
done
```

## Output Files

- `test_results.json` - Test execution summary
- `test_data.csv` - Detailed data points (if exported)
- Analysis reports (console output or saved to file)

## Performance Notes

- Tests typically run at 0.5 second physics simulation intervals
- Full scenario suite takes ~5-10 minutes
- Data points accumulate at ~2 points per second
- Storage: ~1KB per minute of test data

## Contributing

To add new test scenarios:

1. Add method to `TestScenarios` class
2. Follow naming convention: `scenario_*`
3. Include docstring with expected behavior
4. Add success criteria
5. Include logging at key points
6. Add to `run_all_scenarios()` list

## Documentation Files

- **[AUTODROP_STAGES.md](AUTODROP_STAGES.md)** - Detailed explanation of the 7-stage autoDrop deployment process
- **[PHYSICS_ANALYSIS.md](PHYSICS_ANALYSIS.md)** - Physics simulation issues and parameter analysis
- **[VELOCITY_TRACKING.md](VELOCITY_TRACKING.md)** - How boat velocity is calculated locally in tests
- **[DEPLOYMENT_FIX_SUMMARY.md](DEPLOYMENT_FIX_SUMMARY.md)** - Summary of INITIAL_DEPLOYMENT_LIMIT fix
- **[CHANGES_APPLIED.md](CHANGES_APPLIED.md)** - List of all modifications to test framework and plugin

## References

- [SignalK Specification](https://signalk.org/)
- Catenary equation: `max_distance = √(rode² - (depth + bowHeight)²)`
- Physics time step: 0.5 seconds
- Coordinate system: lat/lon with conversion constants
- AutoDrop scope calculation: `scope = rode_deployed / (depth + bowHeight)`
- Typical 5:1 scope for good holding: `final_rode = 5 × (depth + bowHeight)`

## License

Same as SignalK Anchor Alarm Connector

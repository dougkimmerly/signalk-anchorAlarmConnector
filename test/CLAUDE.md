# Test Framework Documentation

This directory contains the test framework for the SignalK Anchor Alarm Connector plugin's physics simulation and autoDrop/autoRetrieve functionality.

## Directory Structure

```
test/
├── CLAUDE.md              # This file - test framework overview
├── .gitignore             # Ignores logs/, data/, overnight_tests_*/, __pycache__/
│
├── scripts/               # Main runnable scripts
│   ├── overnight_test_runner.py   # Full 48-test matrix orchestrator
│   ├── quick_validation_test.py   # Fast 4-corner validation
│   ├── verify_overnight_setup.py  # Pre-test checklist validator
│   ├── reset_anchor.py            # Reset anchor rode to 0m
│   ├── stop_chain.py              # Stop chain operations
│   └── pre_test_reset.sh          # Shell script for full system reset
│
├── phase_tests/           # Development phase test scripts
│   ├── phase2_heading_test.py     # Heading/rotation behavior tests
│   ├── phase3_autodrop_test.py    # AutoDrop sequence tests
│   ├── phase3_constraint_test.py  # Slack constraint tests
│   ├── phase4_motor_test.py       # Motor control tests
│   └── phase4_motor_signalk_test.py  # Motor via SignalK PUT
│
├── legacy/                # Old/superseded scripts (kept for reference)
│   ├── quick_test.py
│   ├── test_harness.py
│   ├── test_scenarios.py
│   ├── v2_test.py
│   └── ...                # Other deprecated test scripts
│
├── utils/                 # Shared Python utilities
│   ├── __init__.py
│   └── common.py          # Auth, SignalK API, simulation helpers
│
├── unit/                  # Unit tests (JavaScript)
│   └── physics.test.js    # Physics module tests (32 tests)
│
├── analysis/              # Analysis tools
│   ├── analyze_overnight_results.py  # Process overnight test data
│   ├── analyze_physics.py       # Physics parameter analysis
│   ├── analyze_boat_movement.py # Movement pattern analysis
│   ├── analyze_results.py       # General result analyzer
│   ├── score_tests.py           # Test scoring system
│   ├── test_analyzer.py         # Real-time test analysis
│   └── docs/                    # Analysis documentation
│       ├── ANALYSIS_REPORT.md
│       ├── PHYSICS_ANALYSIS.md
│       └── PHYSICS_TUNING_SUMMARY.md
│
├── docs/                  # General documentation
│   ├── README.md              # Original test framework documentation
│   ├── FRAMEWORK_OVERVIEW.md  # Architecture and design
│   ├── AUTODROP_STAGES.md     # AutoDrop state machine documentation
│   ├── OVERNIGHT_TEST_GUIDE.md    # How to run overnight tests
│   └── RESET_INSTRUCTIONS.md  # How to reset the system
│
├── data/                  # Test data (JSON files from test runs)
│   └── *.json             # autodrop_*.json, autoretrieve_*.json
│
├── logs/                  # Test run logs (historical)
│   └── *.log
│
└── overnight_tests_*/     # Overnight test session directories
    ├── raw_data/          # Raw test JSON data
    ├── analysis/          # Generated analysis reports
    ├── TEST_LOG.md        # Session log
    └── PROGRESS.txt       # Progress tracker
```

## When to Use Each Document

### Getting Started
- **docs/OVERNIGHT_TEST_GUIDE.md** - Complete guide to running overnight tests
- **scripts/verify_overnight_setup.py** - Run first to check all prerequisites

### Understanding the System
- **docs/FRAMEWORK_OVERVIEW.md** - Overall architecture and design
- **docs/AUTODROP_STAGES.md** - How the autoDrop state machine works
- **docs/README.md** - Original comprehensive test framework documentation

### Running Tests
- **scripts/overnight_test_runner.py** - Full 48-test matrix (6 winds x 4 depths x 2 types)
- **scripts/quick_validation_test.py** - Fast 4-test validation (corner cases only)
- **scripts/reset_anchor.py** - Reset anchor to 0m rode before tests
- **scripts/stop_chain.py** - Emergency stop chain operations

### Development/Phase Tests
- **phase_tests/phase2_*.py** - Heading and rotation behavior
- **phase_tests/phase3_*.py** - AutoDrop, constraints, slack handling
- **phase_tests/phase4_*.py** - Motor control integration

### Unit Tests
- **unit/physics.test.js** - Physics module unit tests (32 tests)

### Analyzing Results
- **analysis/analyze_overnight_results.py** - Process completed test sessions
- **analysis/docs/ANALYSIS_REPORT.md** - Understanding analysis output
- **analysis/docs/PHYSICS_TUNING_SUMMARY.md** - Physics parameter findings

### Troubleshooting
- **docs/RESET_INSTRUCTIONS.md** - How to reset everything
- **scripts/reset_anchor.py** - Reset anchor rode to 0m
- **scripts/stop_chain.py** - Stop chain operations

## Shared Utilities (utils/common.py)

The `utils/common.py` module provides shared functions used across test scripts:

```python
# Authentication
get_auth_token()              # Get JWT token for API calls

# SignalK API
get_signalk_value(path)       # Read SignalK path value
put_signalk_value(path, val)  # Write SignalK path value
get_position()                # Get current lat/lon

# Anchor Commands
send_anchor_command(cmd)      # Send drop/retrieve/stop/reset

# Simulation Control
get_simulation_state()        # Get full simulation state
configure_simulation(config)  # Update simulation config
configure_environment(wind, depth)  # Set wind/depth
reset_simulation()            # Reset to initial state

# Chain Controller (ESP32)
check_chain_controller()      # Check if ESP32 responding
restart_chain_controller()    # Restart and wait
ensure_chain_controller()     # Verify or restart

# Utilities
verify_server()               # Check SignalK server running
calculate_distance(lat1, lon1, lat2, lon2)  # Haversine distance
calculate_bearing(lat1, lon1, lat2, lon2)   # Bearing between points
```

## Test Matrix

The overnight test runner executes tests across:
- **Wind speeds**: 4, 8, 12, 18, 20, 25 knots
- **Depths**: 3, 5, 8, 12 meters (max 12m for 80m chain @ 5:1 scope)
- **Test types**: autoDrop, autoRetrieve

Total: 48 tests (6 x 4 x 2)

## Quick Commands

```bash
# Navigate to scripts directory
cd /home/doug/src/signalk-anchorAlarmConnector/test/scripts

# Verify setup before testing
python3 verify_overnight_setup.py

# Run quick 4-corner validation
python3 quick_validation_test.py

# Run full overnight test suite
python3 overnight_test_runner.py

# Monitor progress (from test/ directory)
tail -f ../overnight_tests_YYYYMMDD/TEST_LOG.md

# Analyze results (from test/ directory)
python3 ../analysis/analyze_overnight_results.py

# Run physics unit tests (from project root)
node test/unit/physics.test.js
```

## Key Configuration

Tests use these endpoints:
- `http://localhost:80/plugins/signalk-anchoralarmconnector/simulation/*`
- `http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/*`

Chain controller (ESP32) at: `192.168.20.217`

## Notes

- All paths in scripts use `Path(__file__).parent` for portability
- Test data JSON files are stored in `data/` subdirectory
- Each overnight session creates its own `overnight_tests_YYYYMMDD/` directory
- Historical logs preserved in `logs/` for reference
- Legacy scripts in `legacy/` are kept for reference but are superseded

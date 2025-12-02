# Overnight Test Session Guide

## Quick Start

### 1. Prerequisites

Make sure these are running:
```bash
# Check SignalK is running
curl http://localhost:80/signalk

# Check plugin is loaded
curl http://localhost:80/plugins/signalk-anchoralarmconnector
```

### 2. Start the Test Session

```bash
cd /home/doug/src/test_framework
python3 overnight_test_runner.py
```

That's it! The script will:
- Run all 72 tests automatically
- Save progress in real-time
- Create detailed data files for each test
- Run analysis when complete
- Generate recommendations

### 3. Monitor Progress

In another terminal, check progress:
```bash
# Watch the log in real-time
tail -f overnight_tests_YYYYMMDD/TEST_LOG.md

# Check current status
cat overnight_tests_YYYYMMDD/PROGRESS.txt

# See summary while running
ls overnight_tests_YYYYMMDD/raw_data | wc -l
```

### 4. Expected Output

After completion, you'll have:
```
overnight_tests_20251201/
├── raw_data/
│   ├── test_autoDrop_4kn_3m_*.json     (72 test data files)
│   └── ...
├── analysis/
│   ├── test_summary.csv                (Scoring for all tests)
│   ├── RECOMMENDATIONS.md              (Issues and fixes)
│   └── heatmaps/
│       └── (placeholder for charts)
├── TEST_LOG.md                         (Complete test log)
└── PROGRESS.txt                        (Final status)
```

## What Each Test Collects

Every 500ms per test sample:
- **Position**: latitude, longitude
- **Motion**: speed (m/s), heading (degrees)
- **Anchor**: rode deployed, chain direction, scope ratio
- **Environment**: wind speed, depth
- **Forces**: wind, drag, motor, chain weight (if available)
- **Motor**: state, throttle, manual mode
- **Constraints**: velocity constraint active, tension ratio

## Test Data Structure

Each test file is JSON with this structure:
```json
{
  "test_metadata": {
    "test_type": "autoDrop",
    "wind_speed_kn": 12,
    "depth_m": 5,
    "duration_sec": 180,
    "sample_count": 360,
    "completed": true
  },
  "samples": [
    {
      "timestamp": "2024-12-01T22:00:00Z",
      "elapsed_sec": 0.0,
      "position": { "latitude": 43.597, "longitude": -79.507, "speed": 0.0, "heading": 180 },
      "distance_from_start": 0.0,
      "simulation_state": { ... }
    },
    ...
  ],
  "summary": {
    "final_scope": 5.1,
    "final_rode": 25.5,
    "final_distance": 24.1,
    "max_speed": 1.2
  }
}
```

## Estimated Duration

- 72 tests × ~10 minutes average = ~12 hours runtime
- Tests run sequentially (one at a time)
- Can be interrupted at any time with Ctrl+C
- Session can be resumed - completed tests are skipped automatically

## Troubleshooting

### Test Hangs or Doesn't Start
```bash
# Check if previous test is still running
ps aux | grep python3

# Check server connectivity
curl http://localhost:80/signalk/v1/api/vessels/self

# Check plugin is responding
curl http://localhost:80/plugins/signalk-anchoralarmconnector/simulation/state
```

### No Data Collected
Check the log:
```bash
tail -50 overnight_tests_YYYYMMDD/TEST_LOG.md
```

Common causes:
- SignalK server not running
- Plugin not loaded
- Token authentication failed
- Reset scripts have issues

### Too Many Failures
The test runner logs each failure. Check:
```bash
grep "FAILED\|Error" overnight_tests_YYYYMMDD/TEST_LOG.md
```

## Analysis After Tests

Once tests complete, run analysis:
```bash
python3 test_analyzer.py overnight_tests_20251201
```

This generates:
- **test_summary.csv** - Scores for all tests
- **RECOMMENDATIONS.md** - Issues and recommended fixes

## Test Matrix Reference

Tests run across:
- **Wind speeds**: 4, 8, 12, 18, 20, 25 knots
- **Depths**: 3, 5, 8, 12, 18, 25 meters
- **Operations**: autoDrop, autoRetrieve

For each combination:
- AutoDrop: Deploys anchor to target 5:1 scope
- AutoRetrieve: Retrieves anchor back to 0m rode

## Key Metrics

For each test, the system tracks:
- **Scope Ratio**: Rode / (Depth + Bow Height)
- **Oscillation**: Velocity sign changes per second
- **Motor Duty**: Percentage of time motor runs
- **Slack**: Chain slack maintained (should be ≥ 0)
- **Heading Error**: Degrees off from bearing to anchor

## Data File Naming

Format: `test_<TYPE>_<WIND>kn_<DEPTH>m_<TIMESTAMP>.json`

Examples:
- `test_autoDrop_4kn_3m_20251201_220000.json`
- `test_autoRetrieve_25kn_25m_20251201_235959.json`

## Recovery and Resume

If the session is interrupted:
1. Note the last completed test number from PROGRESS.txt
2. Re-run `python3 overnight_test_runner.py`
3. Script detects existing data files and skips completed tests
4. Continues from next test in sequence

## Output Interpretation

### Test Summary CSV
Columns:
- `Test`: Test number
- `Type`: autoDrop or autoRetrieve
- `Wind_kn`: Wind speed used
- `Depth_m`: Water depth used
- `Duration_sec`: How long test ran
- `Final_Scope`: Scope ratio achieved (for autoDrop)
- `Final_Rode`: Meters of chain left (for autoRetrieve)
- `Score`: 0-100 overall score
- `Pass`: PASS if score ≥ 50, else FAIL

### Recommendations File
Lists:
- Overall pass rate
- Issues found and which tests are affected
- Priority recommendations for fixes
- Pattern analysis by wind/depth

## Questions?

Check the TEST_LOG.md for detailed timestamps and status of each test, and look at individual JSON files for raw data to debug specific tests.

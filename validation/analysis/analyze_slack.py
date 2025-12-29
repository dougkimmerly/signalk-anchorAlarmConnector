#!/usr/bin/env python3
"""
Analyze chain slack values from overnight test results.
Focuses on slack-based motor control validation.
"""

import json
from pathlib import Path
from statistics import mean, stdev

# Test session directory
session_dir = Path("/home/doug/src/signalk-anchorAlarmConnector/validation/data/overnight_tests_20251206_110625")
raw_data_dir = session_dir / "raw_data"

# Find all autoDrop test files
autodrop_files = sorted(raw_data_dir.glob("test_autoDrop_*.json"))

print("=" * 80)
print("CHAIN SLACK ANALYSIS - Overnight Tests 20251206_110625")
print("=" * 80)
print()

for test_file in autodrop_files:
    print(f"\n{'=' * 80}")
    print(f"File: {test_file.name}")
    print("=" * 80)

    with open(test_file) as f:
        data = json.load(f)

    metadata = data['test_metadata']
    samples = data['samples']

    print(f"\nTest: {metadata['test_type']} at {metadata['wind_speed_kn']}kn wind, {metadata['depth_m']}m depth")
    print(f"Duration: {metadata['duration_sec']:.1f}s ({metadata['sample_count']} samples)")
    print(f"Result: {'TIMEOUT' if metadata.get('timeout') else 'COMPLETED'}")

    # Extract slack data from samples
    slack_values = []
    motor_forces = []
    rode_deployed = []
    distances = []
    motor_states = []  # Track motor on/off

    for sample in samples:
        sim_state = sample.get('simulation_state', {})
        forces = sim_state.get('forces', {})
        constraint = forces.get('constraint', {})
        motor = forces.get('motor', {})

        slack = constraint.get('slack')
        motor_mag = motor.get('magnitude', 0)
        rode = sample.get('rodeDeployed', 0)
        dist = sample.get('distance_from_start', 0)

        if slack is not None:
            slack_values.append(slack)
            motor_forces.append(motor_mag)
            rode_deployed.append(rode)
            distances.append(dist)
            motor_states.append('ON' if motor_mag > 0 else 'OFF')

    if not slack_values:
        print("\n⚠️  NO SLACK DATA FOUND in samples")
        continue

    print(f"\n--- CHAIN SLACK STATISTICS ---")
    print(f"Total samples with slack data: {len(slack_values)}")
    print(f"  Min slack:  {min(slack_values):7.3f}m")
    print(f"  Max slack:  {max(slack_values):7.3f}m")
    print(f"  Avg slack:  {mean(slack_values):7.3f}m")
    if len(slack_values) > 1:
        print(f"  Std dev:    {stdev(slack_values):7.3f}m")

    # Count negative slack samples
    negative_slack = [s for s in slack_values if s < 0]
    print(f"\nNegative slack samples: {len(negative_slack)} ({100*len(negative_slack)/len(slack_values):.1f}%)")
    if negative_slack:
        print(f"  Most negative: {min(negative_slack):.3f}m")

    # Analyze slack distribution
    slack_ranges = {
        '< 0m (NEGATIVE)': [s for s in slack_values if s < 0],
        '0-1m (HIGH motor)': [s for s in slack_values if 0 <= s < 1],
        '1-3m (MED motor)': [s for s in slack_values if 1 <= s < 3],
        '> 3m (LOW/OFF motor)': [s for s in slack_values if s >= 3]
    }

    print(f"\n--- SLACK DISTRIBUTION ---")
    for range_name, range_values in slack_ranges.items():
        count = len(range_values)
        pct = 100 * count / len(slack_values) if slack_values else 0
        print(f"  {range_name}: {count:4d} samples ({pct:5.1f}%)")

    # Analyze motor performance
    print(f"\n--- MOTOR PERFORMANCE ---")
    motor_on_samples = [m for m in motor_forces if m > 0]
    if motor_on_samples:
        print(f"Motor ON samples: {len(motor_on_samples)} ({100*len(motor_on_samples)/len(motor_forces):.1f}%)")
        print(f"  Min force:  {min(motor_on_samples):7.1f}N")
        print(f"  Max force:  {max(motor_on_samples):7.1f}N")
        print(f"  Avg force:  {mean(motor_on_samples):7.1f}N")
    else:
        print(f"Motor ON samples: 0 (0.0%)")

    motor_off_samples = [m for m in motor_forces if m == 0]
    print(f"Motor OFF samples: {len(motor_off_samples)} ({100*len(motor_off_samples)/len(motor_forces):.1f}%)")

    # Correlate motor state with slack ranges
    print(f"\n--- MOTOR STATE vs SLACK CORRELATION ---")
    for i, (slack, motor_force) in enumerate(zip(slack_values, motor_forces)):
        if slack < 0:
            range_name = '< 0m (NEGATIVE)'
        elif slack < 1:
            range_name = '0-1m (HIGH)'
        elif slack < 3:
            range_name = '1-3m (MED)'
        else:
            range_name = '> 3m (LOW/OFF)'

        # Sample every 50th point to avoid overwhelming output
        if i % 50 == 0:
            motor_state = 'ON' if motor_force > 0 else 'OFF'
            print(f"  Sample {i:4d}: slack={slack:6.2f}m [{range_name:20s}] motor={motor_state:3s} ({motor_force:6.1f}N)")

    # Final deployment metrics
    print(f"\n--- DEPLOYMENT METRICS ---")
    print(f"  Final rode deployed: {rode_deployed[-1]:.2f}m")
    print(f"  Final distance from start: {distances[-1]:.2f}m")
    print(f"  Target rode for 5:1 scope: {5 * (metadata['depth_m'] + 2):.2f}m")  # depth + 2m bow height

    # Check if test failed
    target_scope = metadata.get('target_scope', 5.0)
    final_scope = rode_deployed[-1] / (metadata['depth_m'] + 2) if (metadata['depth_m'] + 2) > 0 else 0
    print(f"  Final scope: {final_scope:.2f}:1 (target: {target_scope:.1f}:1)")

    if final_scope < target_scope:
        print(f"\n❌ TEST FAILED: Scope {final_scope:.2f}:1 < target {target_scope:.1f}:1")
    else:
        print(f"\n✅ TEST PASSED: Scope {final_scope:.2f}:1 >= target {target_scope:.1f}:1")

print("\n" + "=" * 80)
print("END OF SLACK ANALYSIS")
print("=" * 80)

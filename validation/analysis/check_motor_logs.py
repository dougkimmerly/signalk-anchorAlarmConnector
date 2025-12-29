#!/usr/bin/env python3
"""
Check for motor engagement patterns and conditions in test data.
Look for why motor isn't engaging despite slack values requiring it.
"""

import json
from pathlib import Path

# Test file
test_file = Path("/home/doug/src/signalk-anchorAlarmConnector/validation/data/overnight_tests_20251206_110625/raw_data/test_autoDrop_1kn_3m_20251206_111434.json")

print("=" * 80)
print("MOTOR ENGAGEMENT CONDITION ANALYSIS")
print("=" * 80)

with open(test_file) as f:
    data = json.load(f)

samples = data['samples']

print(f"\nAnalyzing {len(samples)} samples from Test 1 (3m depth, 1kn wind)")
print()

# Check motor force configuration
first_sample = samples[0]
motor_config = first_sample['simulation_state']['config']['motor']

print("--- MOTOR CONFIGURATION ---")
print(f"Auto-motor enabled: {motor_config.get('autoMotorEnabled')}")
print(f"Deploy min speed: {motor_config.get('deployMinSpeed')} m/s")
print(f"Deploy target speed: {motor_config.get('deployTargetSpeed')} m/s")
print(f"Throttle ramp rate: {motor_config.get('throttleRampRate')}")
print(f"Deploy min throttle: {motor_config.get('deployMinThrottle')}")
print(f"Deploy max throttle: {motor_config.get('deployMaxThrottle')}")
print()

# Analyze conditions throughout test
print("--- MOTOR ENGAGEMENT CONDITIONS ---")
print("Checking first 50 samples in detail:")
print()
print("Sample | Time | Speed | Slack | Command  | Motor State | Why Motor OFF?")
print("-" * 90)

for i in range(min(50, len(samples))):
    sample = samples[i]
    sim_state = sample['simulation_state']
    boat = sim_state['boat']
    forces = sim_state['forces']
    motor = forces.get('motor', {})
    constraint = forces.get('constraint', {})

    time = sample['elapsed_sec']
    speed = boat.get('speed', 0)
    slack = constraint.get('slack')
    command = sample.get('anchorCommand', 'unknown')
    motor_mag = motor.get('magnitude', 0)
    motor_dir = motor.get('direction', 'unknown')

    motor_state = f"{motor_dir} ({motor_mag:.0f}N)"

    # Determine why motor should or shouldn't be ON
    deploy_min_speed = motor_config.get('deployMinSpeed', 0.3)
    deploy_target_speed = motor_config.get('deployTargetSpeed', 0.8)

    # Calculate expected target speed based on slack
    if slack is not None:
        if slack < 1.0:
            expected_target = 0  # Should stop
            slack_range = "< 1m (STOP)"
        elif slack < 3.0:
            expected_target = 0.4  # Medium
            slack_range = "1-3m (MED)"
        else:
            expected_target = 0.8  # High
            slack_range = "> 3m (HIGH)"

        # Should motor be ON?
        should_motor_on = speed < deploy_min_speed and expected_target > 0

        why_off = ""
        if motor_mag == 0:
            if not should_motor_on:
                if expected_target == 0:
                    why_off = f"Slack {slack_range} - target=0"
                elif speed >= deploy_min_speed:
                    why_off = f"Speed OK ({speed:.2f} >= {deploy_min_speed})"
            else:
                why_off = f"SHOULD BE ON! (speed={speed:.2f} < {deploy_min_speed}, slack={slack_range})"

        print(f"{i:6d} | {time:6.1f}s | {speed:5.3f} | {slack:5.2f}m | {command:10s} | {motor_state:20s} | {why_off}")

print()
print("=" * 90)
print()

# Summary statistics
motor_should_be_on_count = 0
motor_is_on_count = 0
motor_correctly_off_count = 0

for sample in samples:
    sim_state = sample['simulation_state']
    boat = sim_state['boat']
    forces = sim_state['forces']
    motor = forces.get('motor', {})
    constraint = forces.get('constraint', {})

    speed = boat.get('speed', 0)
    slack = constraint.get('slack')
    command = sample.get('anchorCommand', 'unknown')
    motor_mag = motor.get('magnitude', 0)

    if command in ['autoDrop', 'down'] and slack is not None:
        # Determine expected target speed
        if slack < 1.0:
            expected_target = 0
        elif slack < 3.0:
            expected_target = 0.4
        else:
            expected_target = 0.8

        should_motor_on = speed < motor_config.get('deployMinSpeed', 0.3) and expected_target > 0

        if should_motor_on:
            motor_should_be_on_count += 1
            if motor_mag > 0:
                motor_is_on_count += 1
        else:
            if motor_mag == 0:
                motor_correctly_off_count += 1

print("--- SUMMARY ---")
print(f"Total samples where motor SHOULD be ON: {motor_should_be_on_count}")
print(f"Samples where motor IS ON when it should be: {motor_is_on_count}")
print(f"Samples where motor correctly OFF: {motor_correctly_off_count}")
print()

if motor_should_be_on_count > 0:
    compliance_rate = 100 * motor_is_on_count / motor_should_be_on_count
    print(f"Motor compliance rate: {compliance_rate:.1f}% (motor ON when it should be)")
    print()

    if compliance_rate < 50:
        print("⚠️  CRITICAL: Motor is NOT engaging when it should!")
        print("This explains the test failure and wrong direction.")
        print()
        print("Possible causes:")
        print("  1. Auto-motor logic not triggering (check command state)")
        print("  2. Manual mode preventing auto-motor")
        print("  3. Force not enabled (check forces.motor.enabled)")
        print("  4. Logic error in updateAutoMotor()")
else:
    print("ℹ️  No samples found where motor should be ON")
    print("This could indicate slack was always < 1m or speed was always sufficient")

print()
print("=" * 80)

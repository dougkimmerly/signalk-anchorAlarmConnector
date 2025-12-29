#!/usr/bin/env python3
"""
Deep dive analysis of Test 1 (3m depth) failure.
Focus on:
1. Why movement is 114.3° instead of ~0° North
2. Why motor only engaged for 4.6% of samples
3. Slack behavior during deployment
"""

import json
from pathlib import Path
import math

def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate bearing between two points in degrees."""
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    if abs(dlat) < 1e-10 and abs(dlon) < 1e-10:
        return 0.0

    bearing = math.degrees(math.atan2(dlon, dlat))
    return (bearing + 360) % 360

# Test file
test_file = Path("/home/doug/src/signalk-anchorAlarmConnector/validation/data/overnight_tests_20251206_110625/raw_data/test_autoDrop_1kn_3m_20251206_111434.json")

print("=" * 80)
print("DETAILED ANALYSIS: Test 1 (autoDrop 1kn 3m depth) - FAILURE INVESTIGATION")
print("=" * 80)

with open(test_file) as f:
    data = json.load(f)

metadata = data['test_metadata']
samples = data['samples']

print(f"\nTest Duration: {metadata['duration_sec']:.1f}s ({len(samples)} samples)")
print(f"Wind: {metadata['wind_speed_kn']}kn from {metadata['wind_direction']}° (South)")
print(f"Expected boat movement: ~0° North (away from wind)")
print()

# Get initial and final positions
first_sample = samples[0]
last_sample = samples[-1]

start_lat = first_sample['position']['latitude']
start_lon = first_sample['position']['longitude']
end_lat = last_sample['position']['latitude']
end_lon = last_sample['position']['longitude']

# Calculate actual bearing
actual_bearing = calculate_bearing(start_lat, start_lon, end_lat, end_lon)

print("--- MOVEMENT ANALYSIS ---")
print(f"Start position: {start_lat:.8f}°N, {start_lon:.8f}°E")
print(f"End position:   {end_lat:.8f}°N, {end_lon:.8f}°E")
print(f"Actual bearing: {actual_bearing:.1f}°")
print(f"Error from North: {abs(actual_bearing):.1f}° (should be ~0°)")
print()

# Analyze trajectory over time
print("--- TRAJECTORY TIMELINE ---")
print("Time(s)  | Lat Change | Lon Change | Bearing | Distance | Rode | Slack | Motor | Stage")
print("-" * 100)

prev_lat = start_lat
prev_lon = start_lon
motor_on_count = 0
motor_off_count = 0

# Sample every 20 seconds
sample_interval = 20  # seconds
sample_indices = [i for i, s in enumerate(samples) if int(s['elapsed_sec']) % sample_interval == 0]

for i in sample_indices[:30]:  # First 30 intervals (10 minutes)
    sample = samples[i]
    sim_state = sample.get('simulation_state', {})
    forces = sim_state.get('forces', {})

    curr_lat = sample['position']['latitude']
    curr_lon = sample['position']['longitude']

    dlat = curr_lat - prev_lat
    dlon = curr_lon - prev_lon

    bearing = calculate_bearing(prev_lat, prev_lon, curr_lat, curr_lon)
    distance = sample['distance_from_start']
    rode = sample['rodeDeployed']

    constraint = forces.get('constraint', {})
    motor = forces.get('motor', {})
    slack = constraint.get('slack', 0)
    motor_force = motor.get('magnitude', 0)
    motor_state = 'ON' if motor_force > 0 else 'OFF'

    stage = sample.get('autoStage', 'Unknown')

    if motor_force > 0:
        motor_on_count += 1
    else:
        motor_off_count += 1

    print(f"{sample['elapsed_sec']:7.1f} | {dlat:10.8f} | {dlon:10.8f} | {bearing:7.1f}° | {distance:6.2f}m | {rode:4.1f}m | {slack:5.2f}m | {motor_state:3s} | {stage}")

print()
print(f"Motor ON samples: {motor_on_count} ({100*motor_on_count/(motor_on_count+motor_off_count):.1f}%)")
print(f"Motor OFF samples: {motor_off_count} ({100*motor_off_count/(motor_on_count+motor_off_count):.1f}%)")

# Analyze motor engagement vs slack
print("\n--- MOTOR ENGAGEMENT vs SLACK ---")
motor_on_samples = []
motor_off_samples = []

for sample in samples:
    sim_state = sample.get('simulation_state', {})
    forces = sim_state.get('forces', {})
    constraint = forces.get('constraint', {})
    motor = forces.get('motor', {})

    slack = constraint.get('slack')
    motor_force = motor.get('magnitude', 0)

    if slack is not None:
        if motor_force > 0:
            motor_on_samples.append({
                'slack': slack,
                'force': motor_force,
                'time': sample['elapsed_sec']
            })
        else:
            motor_off_samples.append({
                'slack': slack,
                'time': sample['elapsed_sec']
            })

print(f"\nTotal motor ON events: {len(motor_on_samples)}")
if motor_on_samples:
    print("\nFirst 10 motor ON events:")
    for i, event in enumerate(motor_on_samples[:10]):
        print(f"  t={event['time']:7.1f}s: slack={event['slack']:6.2f}m, force={event['force']:6.1f}N")

    print("\nLast 10 motor ON events:")
    for event in motor_on_samples[-10:]:
        print(f"  t={event['time']:7.1f}s: slack={event['slack']:6.2f}m, force={event['force']:6.1f}N")

    # Analyze slack values when motor was ON
    slack_when_on = [e['slack'] for e in motor_on_samples]
    print(f"\nSlack when motor ON:")
    print(f"  Min: {min(slack_when_on):6.2f}m")
    print(f"  Max: {max(slack_when_on):6.2f}m")
    print(f"  Avg: {sum(slack_when_on)/len(slack_when_on):6.2f}m")

# Analyze why motor didn't engage more
print("\n--- WHY MOTOR DIDN'T ENGAGE ---")

# Count samples in each slack range with motor OFF
slack_ranges_off = {
    '< 0m (should be HIGH motor)': 0,
    '0-1m (should be HIGH motor)': 0,
    '1-3m (should be MED motor)': 0,
    '> 3m (should be LOW/OFF)': 0
}

for event in motor_off_samples:
    slack = event['slack']
    if slack < 0:
        slack_ranges_off['< 0m (should be HIGH motor)'] += 1
    elif slack < 1:
        slack_ranges_off['0-1m (should be HIGH motor)'] += 1
    elif slack < 3:
        slack_ranges_off['1-3m (should be MED motor)'] += 1
    else:
        slack_ranges_off['> 3m (should be LOW/OFF)'] += 1

print("\nMotor OFF samples by slack range (should motor have been ON?):")
for range_name, count in slack_ranges_off.items():
    pct = 100 * count / len(motor_off_samples) if motor_off_samples else 0
    print(f"  {range_name}: {count:4d} samples ({pct:5.1f}%)")

# Check autoDrop stage transitions
print("\n--- AUTODROP STAGE TRANSITIONS ---")
prev_stage = None
for sample in samples[::10]:  # Every 10th sample
    stage = sample.get('autoStage', 'Unknown')
    if stage != prev_stage:
        print(f"t={sample['elapsed_sec']:7.1f}s: {prev_stage or 'START'} -> {stage}")
        prev_stage = stage

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)

# Summary findings
print("\n1. MOVEMENT DIRECTION ISSUE:")
print(f"   - Boat moved {actual_bearing:.1f}° instead of ~0° North")
print(f"   - This is {abs(actual_bearing - 180):.1f}° off from expected direction")
print(f"   - Wind is from {metadata['wind_direction']}°, boat should drift North (away from wind)")

print("\n2. MOTOR ENGAGEMENT ISSUE:")
print(f"   - Motor only ON for {len(motor_on_samples)} samples ({100*len(motor_on_samples)/len(samples):.1f}%)")
print(f"   - Motor OFF for {len(motor_off_samples)} samples ({100*len(motor_off_samples)/len(samples):.1f}%)")
print(f"   - Motor OFF even when slack < 1m: {slack_ranges_off['0-1m (should be HIGH motor)']} samples")
print(f"   - Motor OFF even with negative slack: {slack_ranges_off['< 0m (should be HIGH motor)']} samples")

print("\n3. POSSIBLE ROOT CAUSE:")
print("   - Motor control logic may not be triggering correctly")
print("   - Slack values are being calculated (present in data)")
print("   - But motor is not responding to slack thresholds as expected")
print("   - Need to check motor.js slack-based control implementation")

print("\n" + "=" * 80)

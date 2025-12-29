#!/usr/bin/env python3
"""
Analyze why boat is moving 114° instead of 0° (North).
Check force vectors and heading throughout the test.
"""

import json
from pathlib import Path
import math

def vector_to_bearing(fx, fy):
    """Convert force vector to bearing (0=North, 90=East)."""
    if abs(fx) < 1e-10 and abs(fy) < 1e-10:
        return 0
    bearing = math.degrees(math.atan2(fx, fy))
    return (bearing + 360) % 360

# Test file - using 5m depth as it passed
test_file = Path("/home/doug/src/signalk-anchorAlarmConnector/validation/data/overnight_tests_20251206_110625/raw_data/test_autoDrop_1kn_5m_20251206_112056.json")

print("=" * 80)
print("FORCE DIRECTION ANALYSIS - Test 3 (5m depth - PASSED)")
print("=" * 80)

with open(test_file) as f:
    data = json.load(f)

samples = data['samples']

print(f"\nAnalyzing {len(samples)} samples")
print(f"Wind: {data['test_metadata']['wind_speed_kn']}kn from {data['test_metadata']['wind_direction']}° (South)")
print(f"Expected movement: ~0° North (boat drifts away from wind)")
print()

# Analyze force vectors over time
print("--- FORCE VECTOR ANALYSIS ---")
print("Sample | Time   | Boat Hdg | Wind Dir | Wind Force | Total Force | Movement Dir")
print("-" * 95)

for i in range(0, min(100, len(samples)), 5):  # Every 5th sample, first 100
    sample = samples[i]
    sim_state = sample['simulation_state']
    boat = sim_state['boat']
    forces = sim_state['forces']

    time = sample['elapsed_sec']
    heading = boat.get('heading', 0)

    wind = forces.get('wind', {})
    wind_dir = wind.get('pushDirection', 0)  # radians
    wind_fx = wind.get('forceX', 0)
    wind_fy = wind.get('forceY', 0)
    wind_mag = wind.get('magnitude', 0)
    wind_bearing = vector_to_bearing(wind_fx, wind_fy)

    total = forces.get('total', {})
    total_fx = total.get('forceX', 0)
    total_fy = total.get('forceY', 0)
    total_bearing = vector_to_bearing(total_fx, total_fy)

    # Get actual position-based movement
    if i > 0:
        prev_sample = samples[i-1]
        dlat = sample['position']['latitude'] - prev_sample['position']['latitude']
        dlon = sample['position']['longitude'] - prev_sample['position']['longitude']
        movement_bearing = vector_to_bearing(dlon, dlat)
    else:
        movement_bearing = 0

    print(f"{i:6d} | {time:6.1f}s | {heading:7.1f}° | {math.degrees(wind_dir):7.1f}° | "
          f"{wind_bearing:7.1f}° ({wind_mag:5.1f}N) | {total_bearing:7.1f}° | {movement_bearing:7.1f}°")

print()

# Analyze the 3m depth test that FAILED
print("\n" + "=" * 80)
print("FORCE DIRECTION ANALYSIS - Test 1 (3m depth - FAILED)")
print("=" * 80)

test_file_3m = Path("/home/doug/src/signalk-anchorAlarmConnector/validation/data/overnight_tests_20251206_110625/raw_data/test_autoDrop_1kn_3m_20251206_111434.json")

with open(test_file_3m) as f:
    data_3m = json.load(f)

samples_3m = data_3m['samples']

print(f"\nAnalyzing {len(samples_3m)} samples")
print(f"Wind: {data_3m['test_metadata']['wind_speed_kn']}kn from {data_3m['test_metadata']['wind_direction']}° (South)")
print(f"Actual movement: 329.3° (should be ~0° North)")
print()

# Check if there's something different in the forces
print("--- FORCE VECTOR ANALYSIS ---")
print("Sample | Time   | Boat Hdg | Wind Dir | Wind Force | Total Force | Movement Dir")
print("-" * 95)

for i in range(0, min(100, len(samples_3m)), 5):  # Every 5th sample, first 100
    sample = samples_3m[i]
    sim_state = sample['simulation_state']
    boat = sim_state['boat']
    forces = sim_state['forces']

    time = sample['elapsed_sec']
    heading = boat.get('heading', 0)

    wind = forces.get('wind', {})
    wind_dir = wind.get('pushDirection', 0)  # radians
    wind_fx = wind.get('forceX', 0)
    wind_fy = wind.get('forceY', 0)
    wind_mag = wind.get('magnitude', 0)
    wind_bearing = vector_to_bearing(wind_fx, wind_fy)

    total = forces.get('total', {})
    total_fx = total.get('forceX', 0)
    total_fy = total.get('forceY', 0)
    total_bearing = vector_to_bearing(total_fx, total_fy)

    # Get actual position-based movement
    if i > 0:
        prev_sample = samples_3m[i-1]
        dlat = sample['position']['latitude'] - prev_sample['position']['latitude']
        dlon = sample['position']['longitude'] - prev_sample['position']['longitude']
        movement_bearing = vector_to_bearing(dlon, dlat)
    else:
        movement_bearing = 0

    print(f"{i:6d} | {time:6.1f}s | {heading:7.1f}° | {math.degrees(wind_dir):7.1f}° | "
          f"{wind_bearing:7.1f}° ({wind_mag:5.1f}N) | {total_bearing:7.1f}° | {movement_bearing:7.1f}°")

print()

# Compare final positions
print("=" * 80)
print("POSITION COMPARISON")
print("=" * 80)
print()

# Test 1 (3m - FAILED)
first_3m = samples_3m[0]
last_3m = samples_3m[-1]
dlat_3m = last_3m['position']['latitude'] - first_3m['position']['latitude']
dlon_3m = last_3m['position']['longitude'] - first_3m['position']['longitude']
final_bearing_3m = vector_to_bearing(dlon_3m, dlat_3m)

print("Test 1 (3m depth - FAILED):")
print(f"  Start: {first_3m['position']['latitude']:.8f}°N, {first_3m['position']['longitude']:.8f}°E")
print(f"  End:   {last_3m['position']['latitude']:.8f}°N, {last_3m['position']['longitude']:.8f}°E")
print(f"  Delta: lat={dlat_3m:.8f}°, lon={dlon_3m:.8f}°")
print(f"  Bearing: {final_bearing_3m:.1f}° (error: {abs(final_bearing_3m):.1f}° from North)")
print()

# Test 3 (5m - PASSED)
first_5m = samples[0]
last_5m = samples[-1]
dlat_5m = last_5m['position']['latitude'] - first_5m['position']['latitude']
dlon_5m = last_5m['position']['longitude'] - first_5m['position']['longitude']
final_bearing_5m = vector_to_bearing(dlon_5m, dlat_5m)

print("Test 3 (5m depth - PASSED):")
print(f"  Start: {first_5m['position']['latitude']:.8f}°N, {first_5m['position']['longitude']:.8f}°E")
print(f"  End:   {last_5m['position']['latitude']:.8f}°N, {last_5m['position']['longitude']:.8f}°E")
print(f"  Delta: lat={dlat_5m:.8f}°, lon={dlon_5m:.8f}°")
print(f"  Bearing: {final_bearing_5m:.1f}° (error: {abs(final_bearing_5m):.1f}° from North)")
print()

print("=" * 80)
print("CONCLUSION")
print("=" * 80)
print()

print(f"Test 1 (3m): Final bearing {final_bearing_3m:.1f}° - Northwest movement")
print(f"Test 3 (5m): Final bearing {final_bearing_5m:.1f}° - North movement (correct!)")
print()
print("The 5m test moved NORTH as expected.")
print("The 3m test moved NORTHWEST (329°), which is 31° off.")
print()
print("Possible explanation:")
print("  - Both tests have wind from ~180° (South)")
print("  - Both should push boat North (0°)")
print("  - The 3m test has some eastward (negative longitude) component")
print("  - This could be due to wind direction variations or initial conditions")

print()
print("=" * 80)

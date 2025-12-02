#!/usr/bin/env python3
"""
Analyze boat movements during anchor deployment test.
Identify wild movements and physics problems.
"""

import json
import math
import sys

def analyze_deployment(filename):
    """Analyze boat movements from deployment test data"""

    with open(filename, 'r') as f:
        data = json.load(f)

    samples = data['samples']
    wind_speed = data.get('wind_speed_kn', 'unknown')

    print(f"\n{'='*80}")
    print(f"BOAT MOVEMENT ANALYSIS - {wind_speed}kn WIND")
    print(f"{'='*80}")
    print(f"Total samples: {len(samples)} (test duration: {len(samples)}s)\n")

    # Extract data (filter out None values)
    lats = [s['latitude'] for s in samples if s.get('latitude') is not None]
    lons = [s['longitude'] for s in samples if s.get('longitude') is not None]
    distances = [s['distance'] for s in samples if s.get('distance') is not None]
    rode_lengths = [s['rode_deployed'] for s in samples if s.get('rode_deployed') is not None]
    boat_speeds = [s['boat_speed'] for s in samples if s.get('boat_speed') is not None]
    depths = [s.get('depth', 3.0) for s in samples if s.get('depth') is not None]

    # Position statistics
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)
    lat_range = lat_max - lat_min
    lon_range = lon_max - lon_min

    # Convert degrees to meters (approximate)
    lat_range_m = lat_range * 111000  # 1 degree latitude = ~111km
    lon_range_m = lon_range * 111000 * math.cos(math.radians(43))  # adjust for latitude

    dist_min, dist_max = min(distances), max(distances)
    rode_min, rode_max = min(rode_lengths), max(rode_lengths)
    speed_max = max(boat_speeds)

    print("POSITION CHANGES:")
    print(f"  Latitude range:  {lat_range:.8f}° ({lat_range_m:.1f}m)")
    print(f"  Longitude range: {lon_range:.8f}° ({lon_range_m:.1f}m)")
    print(f"  Distance from anchor: {dist_min:.1f}m to {dist_max:.1f}m (delta: {dist_max - dist_min:.1f}m)")
    print(f"  Maximum boat speed: {speed_max:.2f} m/s ({speed_max*1.944:.1f} knots)\n")

    print("RODE DEPLOYMENT:")
    print(f"  Deployed: {rode_min:.1f}m to {rode_max:.1f}m\n")

    # Analyze distance vs rode relationship
    print("DISTANCE vs RODE (expected vs actual):")
    print("  Time | Rode  | Expected | Actual  | Delta | Status")
    print("  -----+-------+----------+---------+-------+--------")

    problem_times = []
    for t in [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300]:
        if t >= len(samples):
            break

        s = samples[t]
        rode = s.get('rode_deployed')
        actual_dist = s.get('distance')

        # Skip if data is missing
        if rode is None or actual_dist is None:
            continue

        # Expected: straight-line distance from depth
        # With catenary, typically 70-95% of straight line
        if rode > 3:
            straight_dist = math.sqrt(rode**2 - 3**2)
            # Catenary reduction factor (typical: 0.75-0.90)
            expected_dist = straight_dist * 0.85
        else:
            expected_dist = 0

        delta = actual_dist - expected_dist

        # Flag issues
        if delta < -2:
            status = "TOO CLOSE!"
        elif delta > 5:
            status = "TOO FAR!"
        elif delta > 2:
            status = "drift"
        else:
            status = "ok"

        if status != "ok":
            problem_times.append((t, rode, expected_dist, actual_dist, delta, status))

        print(f"  {t:3d}s | {rode:5.1f}m | {expected_dist:7.1f}m | {actual_dist:6.1f}m | {delta:+5.1f}m | {status}")

    # Constraint activation analysis
    print(f"\n{'='*80}")
    print("CONSTRAINT ACTIVATION ANALYSIS:")
    print(f"{'='*80}")
    print(f"INITIAL_DEPLOYMENT_LIMIT = 15m")
    print(f"Slack constraint re-enables when rode >= 15m\n")

    # Find when rode reaches 15m
    constraint_time = None
    for i, sample in enumerate(samples):
        if sample['rode_deployed'] >= 15:
            constraint_time = i
            break

    if constraint_time:
        print(f"Constraint re-enabled at: {constraint_time}s (rode={samples[constraint_time]['rode_deployed']:.1f}m)")
        print(f"Before constraint: distance = {samples[constraint_time-1]['distance']:.1f}m")
        print(f"After constraint:  distance = {samples[constraint_time]['distance']:.1f}m")
        print(f"Distance jump: {samples[constraint_time]['distance'] - samples[constraint_time-1]['distance']:.1f}m")

    # Analyze problem areas
    print(f"\n{'='*80}")
    print("PROBLEM AREAS IDENTIFIED:")
    print(f"{'='*80}\n")

    if problem_times:
        print(f"Found {len(problem_times)} time points with positioning issues:\n")
        for t, rode, expected, actual, delta, status in problem_times:
            print(f"  {t:3d}s: rode={rode:.1f}m, expected_dist={expected:.1f}m, actual={actual:.1f}m, delta={delta:+.1f}m ({status})")
    else:
        print("No major position discrepancies detected.\n")

    # Peak analysis
    print(f"\n{'='*80}")
    print("BOAT MOVEMENT PEAKS:")
    print(f"{'='*80}\n")

    # Find maximum distance
    max_dist_idx = distances.index(max(distances))
    max_dist_value = max(distances)
    max_dist_sample = samples[max_dist_idx]
    print(f"Maximum distance: {max_dist_value:.1f}m at {max_dist_idx}s")
    rode = max_dist_sample.get('rode_deployed')
    speed = max_dist_sample.get('boat_speed')
    if rode is not None:
        print(f"  Rode deployed: {rode:.1f}m")
    if speed is not None:
        print(f"  Boat speed: {speed:.2f} m/s")
    print(f"  Boat heading: {max_dist_sample.get('boat_heading', 'N/A')}")

    # Find maximum speed
    if boat_speeds:
        max_speed_idx = boat_speeds.index(max(boat_speeds))
        max_speed = max(boat_speeds)
        max_speed_sample = samples[max_speed_idx]
        print(f"\nMaximum speed: {max_speed:.2f} m/s ({max_speed*1.944:.1f} knots) at {max_speed_idx}s")
        distance = max_speed_sample.get('distance')
        rode = max_speed_sample.get('rode_deployed')
        if distance is not None:
            print(f"  Distance: {distance:.1f}m")
        if rode is not None:
            print(f"  Rode deployed: {rode:.1f}m")
    else:
        print(f"\nNo boat speed data available")

    # Final state
    print(f"\n{'='*80}")
    print("FINAL STATE AT 300s:")
    print(f"{'='*80}\n")
    final = samples[-1]
    print(f"Rode deployed: {final['rode_deployed']:.1f}m")
    print(f"Distance from anchor: {final['distance']:.1f}m")
    print(f"Boat speed: {final['boat_speed']:.2f} m/s")
    print(f"Water depth: {final.get('depth', 3.0):.1f}m")

    # Calculate scope
    scope_denom = final.get('depth', 3.0) + 2.0  # 2m bow height
    scope = final['rode_deployed'] / scope_denom if scope_denom > 0 else 0
    print(f"Final scope: {scope:.1f}:1 (target: 5:1)")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python analyze_boat_movement.py <deployment_json_file>")
        sys.exit(1)

    filename = sys.argv[1]
    try:
        analyze_deployment(filename)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

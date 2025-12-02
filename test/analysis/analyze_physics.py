#!/usr/bin/env python3
"""
Analyze test results to identify physics parameter adjustments needed
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Directory containing test framework (parent of analysis/)
TEST_DIR = Path(__file__).parent.parent

def load_test_file(filepath):
    """Load a test result JSON file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def analyze_test(filepath):
    """Analyze a single test result"""
    data = load_test_file(filepath)
    if not data or 'samples' not in data or len(data['samples']) == 0:
        return None
    
    test_type = data.get('test_type', 'unknown')
    wind_speed = data.get('wind_speed_kn', 0)
    samples = data['samples']
    
    # Extract metrics (filter out None values)
    distances = [s.get('distance', 0) for s in samples if s.get('distance') is not None]
    rodes = [s.get('rode_deployed', 0) for s in samples if s.get('rode_deployed') is not None]
    slacks = [s.get('chain_slack', 0) for s in samples if s.get('chain_slack') is not None]
    boat_speeds = [s.get('boat_speed', 0) for s in samples if s.get('boat_speed') is not None]
    
    if not distances or not rodes or not slacks:
        return None
    
    # Calculate statistics
    min_distance = min(distances)
    max_distance = max(distances)
    final_rode = rodes[-1] if rodes else 0
    min_slack = min(slacks)
    max_slack = max(slacks)
    neg_slack_count = sum(1 for s in slacks if s < 0)
    avg_boat_speed = sum(boat_speeds) / len(boat_speeds) if boat_speeds else 0
    max_boat_speed = max(boat_speeds) if boat_speeds else 0
    
    # Calculate drift rate (distance covered per second)
    time_span = samples[-1].get('time_sec', 1) - samples[0].get('time_sec', 0)
    if time_span > 0 and len(distances) > 1:
        drift_rate = (distances[-1] - distances[0]) / time_span
    else:
        drift_rate = 0
    
    return {
        'test_type': test_type,
        'wind_speed': wind_speed,
        'samples': len(samples),
        'duration': time_span,
        'min_distance': min_distance,
        'max_distance': max_distance,
        'final_rode': final_rode,
        'min_slack': min_slack,
        'max_slack': max_slack,
        'neg_slack_count': neg_slack_count,
        'neg_slack_pct': (neg_slack_count / len(slacks) * 100) if slacks else 0,
        'avg_boat_speed': avg_boat_speed,
        'max_boat_speed': max_boat_speed,
        'drift_rate': drift_rate,
        'filepath': filepath
    }

def main():
    data_dir = TEST_DIR / 'data'

    # Get most recent test files from data directory
    files = [f for f in os.listdir(data_dir) if f.startswith(('autodrop_', 'autoretrieve_')) and f.endswith('.json')]
    files = sorted(files, reverse=True)[:12]  # Last 12 files

    results_by_type = {}

    print("\n" + "="*100)
    print("PHYSICS SIMULATION TEST ANALYSIS")
    print("="*100)

    for filepath in files:
        full_path = data_dir / filepath
        result = analyze_test(full_path)
        
        if result:
            key = f"{result['test_type']}_{result['wind_speed']}kn"
            if key not in results_by_type:
                results_by_type[key] = []
            results_by_type[key].append(result)
    
    # Analyze by test type and wind speed
    print("\n### AUTODROP ANALYSIS ###\n")
    
    for wind_speed in [15, 10, 5]:
        key = f"autoDrop_{wind_speed}kn"
        if key in results_by_type:
            result = results_by_type[key][0]  # Most recent
            
            expected_drift = {15: 0.75, 10: 0.50, 5: 0.25}[wind_speed]
            
            print(f"\n{wind_speed}kn AutoDrop:")
            print(f"  Samples: {result['samples']} over {result['duration']:.1f}s")
            print(f"  Final rode deployed: {result['final_rode']:.1f}m (target: ~10m)")
            print(f"  Distance change: {result['min_distance']:.1f}m → {result['max_distance']:.1f}m (δ={result['max_distance']-result['min_distance']:.1f}m)")
            print(f"  Drift rate: {result['drift_rate']:.4f} m/s (expected: {expected_drift} m/s) [{result['drift_rate']/expected_drift*100:.1f}%]")
            print(f"  Slack violations: {result['neg_slack_count']} samples ({result['neg_slack_pct']:.1f}%)")
            print(f"  Slack range: {result['min_slack']:.1f}m to {result['max_slack']:.1f}m")
            print(f"  Boat speed: avg={result['avg_boat_speed']:.3f} m/s, max={result['max_boat_speed']:.3f} m/s")
    
    print("\n### AUTORETRIEVE ANALYSIS ###\n")
    
    for wind_speed in [15, 10, 5]:
        key = f"autoRetrieve_{wind_speed}kn"
        if key in results_by_type:
            result = results_by_type[key][0]  # Most recent
            
            print(f"\n{wind_speed}kn AutoRetrieve:")
            print(f"  Samples: {result['samples']} over {result['duration']:.1f}s")
            print(f"  Final rode deployed: {result['final_rode']:.1f}m (should be close to 0)")
            print(f"  Distance change: {result['min_distance']:.1f}m → {result['max_distance']:.1f}m (δ={result['max_distance']-result['min_distance']:.1f}m)")
            print(f"  Drift rate: {result['drift_rate']:.4f} m/s")
            print(f"  Slack violations: {result['neg_slack_count']} samples ({result['neg_slack_pct']:.1f}%)")
            print(f"  Slack range: {result['min_slack']:.1f}m to {result['max_slack']:.1f}m")
            print(f"  Boat speed: avg={result['avg_boat_speed']:.3f} m/s, max={result['max_boat_speed']:.3f} m/s")
    
    # Physics recommendations
    print("\n" + "="*100)
    print("PHYSICS PARAMETER ANALYSIS")
    print("="*100)
    
    # Check drift rates
    print("\n### DRIFT RATE ASSESSMENT ###")
    drift_15 = results_by_type.get('autoDrop_15kn', [{}])[0].get('drift_rate', 0)
    drift_10 = results_by_type.get('autoDrop_10kn', [{}])[0].get('drift_rate', 0)
    drift_5 = results_by_type.get('autoDrop_5kn', [{}])[0].get('drift_rate', 0)
    
    print(f"\nActual vs Expected drift rates:")
    print(f"  15kn: {drift_15:.4f} m/s (expected ~0.75 m/s) - {drift_15/0.75*100:.1f}% of expected")
    print(f"  10kn: {drift_10:.4f} m/s (expected ~0.50 m/s) - {drift_10/0.50*100:.1f}% of expected")
    if drift_5 > 0:
        print(f"  5kn:  {drift_5:.4f} m/s (expected ~0.25 m/s) - {drift_5/0.25*100:.1f}% of expected")
    
    if drift_15 < 0.3 and drift_10 < 0.2:
        print("\n⚠ ISSUE: Drift rates are TOO LOW - wind force may be insufficient")
        print("  Recommendations:")
        print("  1. Increase wind force coefficient (0.5 in wind force formula)")
        print("  2. Reduce WATER_DRAG constant (currently 150.0)")
        print("  3. Check wind speed values in simulation - may not match 15kn, 10kn")
    
    # Check slack violations
    print("\n### SLACK CONSTRAINT ASSESSMENT ###")
    slack_15 = results_by_type.get('autoDrop_15kn', [{}])[0].get('neg_slack_pct', 0)
    slack_10 = results_by_type.get('autoDrop_10kn', [{}])[0].get('neg_slack_pct', 0)
    
    print(f"\nNegative slack violations:")
    print(f"  15kn: {slack_15:.1f}% of samples")
    print(f"  10kn: {slack_10:.1f}% of samples")
    
    if slack_15 > 10 or slack_10 > 10:
        print("\n⚠ ISSUE: High slack violation rate - boat moving too far from anchor during deployment")
        print("  Recommendations:")
        print("  1. Increase INITIAL_DEPLOYMENT_LIMIT (currently 7m) to allow more movement")
        print("  2. Reduce catenary force constraint during early phases")
        print("  3. Adjust tension multiplier to increase rode tension")
    
    print("\n" + "="*100 + "\n")

if __name__ == '__main__':
    main()

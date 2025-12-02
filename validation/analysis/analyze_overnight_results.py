#!/usr/bin/env python3
"""
Overnight Test Results Analyzer
Processes test data from overnight_test_runner.py and generates comprehensive analysis.

Usage:
    python3 analyze_overnight_results.py [session_dir]

If no session_dir is provided, uses the most recent overnight_tests_* directory.
"""

import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Constants
BOW_HEIGHT = 2.0  # meters
METERS_TO_LAT = 0.000009
METERS_TO_LON = 0.0000125

# Directory containing test framework (parent of analysis/)
TEST_DIR = Path(__file__).parent.parent


def find_session_dir():
    """Find the most recent overnight test session directory"""
    sessions = sorted(TEST_DIR.glob('overnight_tests_*'), reverse=True)
    if sessions:
        return sessions[0]
    return None


def load_test_file(filepath):
    """Load a single test JSON file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None


def calculate_scope(rode, depth, bow_height=BOW_HEIGHT):
    """Calculate scope ratio"""
    total_depth = depth + bow_height
    if total_depth <= 0:
        return 0
    return rode / total_depth


def analyze_single_test(test_data):
    """Analyze a single test and extract key metrics"""
    meta = test_data.get('test_metadata', {})
    samples = test_data.get('samples', [])

    if not samples:
        return None

    analysis = {
        'test_type': meta.get('test_type'),
        'wind_speed': meta.get('wind_speed_kn'),
        'depth': meta.get('depth_m'),
        'duration': meta.get('duration_sec'),
        'sample_count': len(samples),
    }

    # Extract position data
    first = samples[0]
    last = samples[-1]

    first_pos = first.get('position', {})
    last_pos = last.get('position', {})

    # Movement analysis
    lat_start = first_pos.get('latitude', 0)
    lon_start = first_pos.get('longitude', 0)
    lat_end = last_pos.get('latitude', 0)
    lon_end = last_pos.get('longitude', 0)

    lat_change = lat_end - lat_start
    lon_change = lon_end - lon_start

    # Convert to meters
    north_movement = lat_change / METERS_TO_LAT if METERS_TO_LAT else 0
    east_movement = lon_change / METERS_TO_LON if METERS_TO_LON else 0
    total_movement = math.sqrt(north_movement**2 + east_movement**2)

    # Movement bearing (0 = North, 90 = East, 180 = South, 270 = West)
    if lat_change != 0 or lon_change != 0:
        bearing = math.atan2(lon_change, lat_change) * 180 / math.pi
        if bearing < 0:
            bearing += 360
    else:
        bearing = None

    analysis['movement'] = {
        'north_m': north_movement,
        'east_m': east_movement,
        'total_m': total_movement,
        'bearing': bearing,
    }

    # Speed analysis
    speeds = [s.get('position', {}).get('speed', 0) for s in samples]
    speeds = [s for s in speeds if s is not None]

    if speeds:
        analysis['speed'] = {
            'max': max(speeds),
            'min': min(speeds),
            'avg': sum(speeds) / len(speeds),
            'final': speeds[-1] if speeds else 0,
        }

    # Heading analysis
    headings = [s.get('position', {}).get('heading') for s in samples]
    headings = [h for h in headings if h is not None]

    if headings:
        # Calculate average heading (handling 0/360 wraparound)
        sin_sum = sum(math.sin(math.radians(h)) for h in headings)
        cos_sum = sum(math.cos(math.radians(h)) for h in headings)
        avg_heading = math.degrees(math.atan2(sin_sum, cos_sum)) % 360

        analysis['heading'] = {
            'initial': headings[0],
            'final': headings[-1],
            'avg': avg_heading,
            'range': max(headings) - min(headings) if len(headings) > 1 else 0,
        }

    # Force analysis from simulation state
    forces_data = []
    for s in samples:
        sim_state = s.get('simulation_state', {})
        forces = sim_state.get('forces', {})
        if forces:
            forces_data.append({
                'wind': forces.get('wind', {}).get('magnitude', 0),
                'drag': forces.get('waterDrag', {}).get('magnitude', 0),
                'motor': forces.get('motor', {}).get('magnitude', 0),
                'chain': forces.get('chainWeight', {}).get('magnitude', 0),
                'constraint': forces.get('constraint', {}).get('magnitude', 0),
                'total': forces.get('total', {}).get('magnitude', 0),
            })

    if forces_data:
        analysis['forces'] = {
            'wind_avg': sum(f['wind'] for f in forces_data) / len(forces_data),
            'wind_max': max(f['wind'] for f in forces_data),
            'drag_avg': sum(f['drag'] for f in forces_data) / len(forces_data),
            'motor_avg': sum(f['motor'] for f in forces_data) / len(forces_data),
            'chain_avg': sum(f['chain'] for f in forces_data) / len(forces_data),
            'constraint_avg': sum(f['constraint'] for f in forces_data) / len(forces_data),
        }

    # Rode/scope analysis for autoDrop
    if meta.get('test_type') == 'autoDrop':
        rode_values = []
        scope_values = []

        for s in samples:
            sim_state = s.get('simulation_state', {})
            boat = sim_state.get('boat', {})
            env = sim_state.get('environment', {})

            # Try to get rode from various sources
            rode = None
            if 'rodeDeployed' in boat:
                rode = boat.get('rodeDeployed')

            if rode is not None:
                rode_values.append(rode)
                depth = env.get('depth', meta.get('depth_m', 3))
                scope_values.append(calculate_scope(rode, depth))

        if rode_values:
            analysis['rode'] = {
                'initial': rode_values[0],
                'final': rode_values[-1],
                'max': max(rode_values),
            }

        if scope_values:
            analysis['scope'] = {
                'initial': scope_values[0],
                'final': scope_values[-1],
                'max': max(scope_values),
                'target_reached': max(scope_values) >= 5.0,
            }

    # Phase detection
    phases = detect_phases(samples)
    if phases:
        analysis['phases'] = phases

    return analysis


def detect_phases(samples):
    """Detect deployment phases based on speed changes"""
    if len(samples) < 10:
        return None

    phases = []
    window_size = 10

    # Calculate smoothed speeds
    speeds = []
    for s in samples:
        speed = s.get('position', {}).get('speed', 0)
        speeds.append(speed if speed else 0)

    # Simple phase detection based on speed trends
    current_phase = 'acceleration'
    phase_start = 0

    for i in range(window_size, len(speeds)):
        window = speeds[i-window_size:i]
        avg_speed = sum(window) / len(window)

        elapsed = samples[i].get('elapsed_sec', i * 0.5)

        if current_phase == 'acceleration':
            if avg_speed > 0.3:  # Reached cruising speed
                phases.append({
                    'phase': 'acceleration',
                    'start': samples[phase_start].get('elapsed_sec', 0),
                    'end': elapsed,
                })
                current_phase = 'steady'
                phase_start = i
        elif current_phase == 'steady':
            if avg_speed < 0.1:  # Slowing down
                phases.append({
                    'phase': 'steady',
                    'start': samples[phase_start].get('elapsed_sec', 0),
                    'end': elapsed,
                })
                current_phase = 'deceleration'
                phase_start = i
        elif current_phase == 'deceleration':
            if avg_speed < 0.02:  # Nearly stopped
                phases.append({
                    'phase': 'deceleration',
                    'start': samples[phase_start].get('elapsed_sec', 0),
                    'end': elapsed,
                })
                current_phase = 'settled'
                phase_start = i
                break

    # Add final phase
    if samples:
        final_elapsed = samples[-1].get('elapsed_sec', len(samples) * 0.5)
        phases.append({
            'phase': current_phase,
            'start': samples[phase_start].get('elapsed_sec', 0) if phase_start < len(samples) else 0,
            'end': final_elapsed,
        })

    return phases


def generate_summary_report(session_dir, all_analyses):
    """Generate a comprehensive summary report"""
    report = []
    report.append("=" * 80)
    report.append("OVERNIGHT TEST RESULTS ANALYSIS")
    report.append(f"Session: {session_dir.name}")
    report.append(f"Analysis Date: {datetime.now().isoformat()}")
    report.append("=" * 80)
    report.append("")

    # Separate autoDrop and autoRetrieve
    autodrop = [a for a in all_analyses if a and a.get('test_type') == 'autoDrop']
    autoretrieve = [a for a in all_analyses if a and a.get('test_type') == 'autoRetrieve']

    report.append(f"Total Tests: {len(all_analyses)}")
    report.append(f"  AutoDrop: {len(autodrop)}")
    report.append(f"  AutoRetrieve: {len(autoretrieve)}")
    report.append("")

    # AutoDrop Analysis
    report.append("-" * 80)
    report.append("AUTODROP ANALYSIS")
    report.append("-" * 80)
    report.append("")

    # Movement direction analysis
    report.append("Movement Direction (should be ~0° North for wind from South):")
    report.append("-" * 60)

    # Group by wind speed
    by_wind = defaultdict(list)
    for a in autodrop:
        wind = a.get('wind_speed')
        if wind:
            by_wind[wind].append(a)

    for wind in sorted(by_wind.keys()):
        tests = by_wind[wind]
        bearings = [t['movement']['bearing'] for t in tests if t.get('movement', {}).get('bearing') is not None]
        movements = [t['movement']['total_m'] for t in tests if t.get('movement', {}).get('total_m')]

        if bearings:
            avg_bearing = sum(bearings) / len(bearings)
            avg_movement = sum(movements) / len(movements) if movements else 0

            # Check if movement is correct (should be North, ~0°)
            bearing_error = min(avg_bearing, 360 - avg_bearing)
            status = "✓" if bearing_error < 30 else "⚠" if bearing_error < 60 else "✗"

            report.append(f"  {wind:2}kn: Bearing={avg_bearing:5.1f}° (error={bearing_error:4.1f}°) {status}  Movement={avg_movement:5.1f}m")

    report.append("")

    # Speed analysis
    report.append("Speed Analysis:")
    report.append("-" * 60)

    for wind in sorted(by_wind.keys()):
        tests = by_wind[wind]
        max_speeds = [t['speed']['max'] for t in tests if t.get('speed', {}).get('max')]
        avg_speeds = [t['speed']['avg'] for t in tests if t.get('speed', {}).get('avg')]

        if max_speeds:
            avg_max = sum(max_speeds) / len(max_speeds)
            avg_avg = sum(avg_speeds) / len(avg_speeds) if avg_speeds else 0
            report.append(f"  {wind:2}kn: Max={avg_max:.3f}m/s ({avg_max*1.94384:.2f}kn)  Avg={avg_avg:.3f}m/s")

    report.append("")

    # Heading analysis
    report.append("Heading Analysis (should be ~180° pointing into South wind):")
    report.append("-" * 60)

    for wind in sorted(by_wind.keys()):
        tests = by_wind[wind]
        headings = [t['heading']['avg'] for t in tests if t.get('heading', {}).get('avg') is not None]

        if headings:
            avg_heading = sum(headings) / len(headings)
            heading_error = abs(avg_heading - 180)
            if heading_error > 180:
                heading_error = 360 - heading_error

            status = "✓" if heading_error < 20 else "⚠" if heading_error < 45 else "✗"
            report.append(f"  {wind:2}kn: Heading={avg_heading:5.1f}° (error={heading_error:4.1f}°) {status}")

    report.append("")

    # Force analysis
    report.append("Force Analysis:")
    report.append("-" * 60)

    for wind in sorted(by_wind.keys()):
        tests = by_wind[wind]
        wind_forces = [t['forces']['wind_avg'] for t in tests if t.get('forces', {}).get('wind_avg')]
        drag_forces = [t['forces']['drag_avg'] for t in tests if t.get('forces', {}).get('drag_avg')]
        motor_forces = [t['forces']['motor_avg'] for t in tests if t.get('forces', {}).get('motor_avg')]

        if wind_forces:
            avg_wind = sum(wind_forces) / len(wind_forces)
            avg_drag = sum(drag_forces) / len(drag_forces) if drag_forces else 0
            avg_motor = sum(motor_forces) / len(motor_forces) if motor_forces else 0
            report.append(f"  {wind:2}kn: Wind={avg_wind:6.1f}N  Drag={avg_drag:6.1f}N  Motor={avg_motor:6.1f}N")

    report.append("")

    # Depth scaling analysis
    report.append("Depth Scaling (movement should scale with depth):")
    report.append("-" * 60)

    by_depth = defaultdict(list)
    for a in autodrop:
        depth = a.get('depth')
        if depth:
            by_depth[depth].append(a)

    for depth in sorted(by_depth.keys()):
        tests = by_depth[depth]
        movements = [t['movement']['total_m'] for t in tests if t.get('movement', {}).get('total_m')]

        if movements:
            avg_movement = sum(movements) / len(movements)
            expected_scope_5 = (depth + BOW_HEIGHT) * 5  # Expected rode for 5:1 scope
            report.append(f"  {depth:2}m depth: Avg movement={avg_movement:5.1f}m  (5:1 scope needs {expected_scope_5:.1f}m rode)")

    report.append("")

    # Cross-matrix summary
    report.append("=" * 80)
    report.append("CROSS-MATRIX SUMMARY (Movement in meters)")
    report.append("=" * 80)
    report.append("")

    # Build matrix
    winds = sorted(set(a.get('wind_speed') for a in autodrop if a.get('wind_speed')))
    depths = sorted(set(a.get('depth') for a in autodrop if a.get('depth')))

    # Header
    header = "Wind\\Depth"
    for d in depths:
        header += f" | {d:5}m"
    report.append(header)
    report.append("-" * len(header))

    for wind in winds:
        row = f"{wind:4}kn   "
        for depth in depths:
            # Find matching test
            match = [a for a in autodrop if a.get('wind_speed') == wind and a.get('depth') == depth]
            if match and match[0].get('movement', {}).get('total_m'):
                movement = match[0]['movement']['total_m']
                row += f" | {movement:5.1f}m"
            else:
                row += " |    -- "
        report.append(row)

    report.append("")

    # AutoRetrieve Analysis
    report.append("-" * 80)
    report.append("AUTORETRIEVE ANALYSIS")
    report.append("-" * 80)
    report.append("")

    if autoretrieve:
        durations = [a.get('duration', 0) for a in autoretrieve]
        avg_duration = sum(durations) / len(durations) if durations else 0
        report.append(f"Average retrieval time: {avg_duration:.1f}s")
        report.append(f"All retrievals completed: {len(autoretrieve)}/{len(autoretrieve)}")

    report.append("")
    report.append("=" * 80)
    report.append("END OF REPORT")
    report.append("=" * 80)

    return "\n".join(report)


def main():
    """Main entry point"""
    # Find session directory
    if len(sys.argv) > 1:
        session_dir = Path(sys.argv[1])
    else:
        session_dir = find_session_dir()

    if not session_dir or not session_dir.exists():
        print("Error: No session directory found")
        print("Usage: python3 analyze_overnight_results.py [session_dir]")
        return 1

    print(f"Analyzing session: {session_dir}")

    # Load all test files
    raw_data_dir = session_dir / 'raw_data'
    if not raw_data_dir.exists():
        print(f"Error: No raw_data directory in {session_dir}")
        return 1

    test_files = sorted(raw_data_dir.glob('*.json'))
    print(f"Found {len(test_files)} test files")

    # Analyze each test
    all_analyses = []
    for filepath in test_files:
        test_data = load_test_file(filepath)
        if test_data:
            analysis = analyze_single_test(test_data)
            if analysis:
                all_analyses.append(analysis)

    print(f"Successfully analyzed {len(all_analyses)} tests")

    # Generate report
    report = generate_summary_report(session_dir, all_analyses)

    # Print to console
    print("\n")
    print(report)

    # Save report
    report_file = session_dir / 'analysis' / 'ANALYSIS_REPORT.txt'
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"\nReport saved to: {report_file}")

    # Save detailed analysis as JSON
    analysis_json = session_dir / 'analysis' / 'detailed_analysis.json'
    with open(analysis_json, 'w') as f:
        json.dump(all_analyses, f, indent=2)
    print(f"Detailed analysis saved to: {analysis_json}")

    return 0


if __name__ == '__main__':
    sys.exit(main())

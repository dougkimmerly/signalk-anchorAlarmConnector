#!/usr/bin/env python3
"""
Quick Validation Test - 4 Corner Case Tests
Runs autoDrop tests at extreme wind/depth combinations to verify config is applied.

Wind: 4kn (light) and 25kn (heavy)
Depth: 3m (shallow) and 25m (deep)

Expected: Clear differentiation in wind forces and movement patterns.
"""

import json
import time
import urllib.request
import urllib.error
import math
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:80"
TEST_DURATION = 60  # seconds per test (shorter for validation)
SAMPLE_INTERVAL = 0.5

# Test matrix - 4 corner cases (max 12m depth for 80m chain @ 5:1 scope)
TEST_CASES = [
    (4, 3, "Light wind, shallow"),
    (25, 3, "Heavy wind, shallow"),
    (4, 12, "Light wind, deep"),
    (25, 12, "Heavy wind, deep"),
]

def get_auth_token():
    url = f"{BASE_URL}/signalk/v1/auth/login"
    data = json.dumps({"username": "admin", "password": "signalk"}).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read()).get('token')

def configure_environment(token, wind_speed, depth):
    url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/simulation/config"
    data = json.dumps({
        "wind": {"initialSpeed": wind_speed, "initialDirection": 180},
        "environment": {"depth": depth}
    }).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='PUT')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read())

def reset_simulation(token):
    url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/simulation/reset"
    req = urllib.request.Request(url, method='PUT')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=5) as response:
        return True

def reset_anchor(token):
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/anchor/rodeDeployed"
        data = json.dumps({"value": 1}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return True
    except Exception as e:
        print(f"  Warning: reset_anchor returned: {e}")
        return True  # Continue anyway

def send_command(token, command):
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/anchor/command"
        data = json.dumps({"value": command}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return True
    except Exception as e:
        print(f"  Warning: Command '{command}' returned: {e}")
        return True  # Continue anyway - command may have worked

def get_simulation_state(token):
    url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/simulation/state"
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read())

def get_position(token):
    url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/position/value"
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read())

def run_single_test(token, wind_speed, depth, description):
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"Wind: {wind_speed}kn, Depth: {depth}m")
    print(f"{'='*60}")

    # Setup
    print("[1] Stopping and resetting...")
    send_command(token, "stop")
    time.sleep(0.5)
    reset_anchor(token)
    time.sleep(2)

    # Configure
    print(f"[2] Configuring: {wind_speed}kn wind, {depth}m depth...")
    configure_environment(token, wind_speed, depth)
    reset_simulation(token)
    time.sleep(1)

    # Verify config applied
    state = get_simulation_state(token)
    env = state.get('environment', {})
    actual_wind = env.get('windSpeed')
    actual_depth = env.get('depth')
    wind_force = state.get('forces', {}).get('wind', {}).get('magnitude', 0)

    if actual_wind != wind_speed or actual_depth != depth:
        print(f"✗ Config NOT applied! Got wind={actual_wind}, depth={actual_depth}")
        return None
    print(f"✓ Config applied: wind={actual_wind}kn, depth={actual_depth}m, force={wind_force:.1f}N")

    # Get start position
    start_pos = get_position(token)
    start_lat = start_pos['latitude']
    start_lon = start_pos['longitude']

    # Start autoDrop
    print("[3] Starting autoDrop...")
    send_command(token, "autoDrop")

    # Collect data
    samples = []
    start_time = time.time()

    print("[4] Collecting data for 60 seconds...")
    while time.time() - start_time < TEST_DURATION:
        try:
            state = get_simulation_state(token)
            pos = get_position(token)

            if state and pos:
                forces = state.get('forces', {})
                samples.append({
                    'elapsed': time.time() - start_time,
                    'lat': pos['latitude'],
                    'lon': pos['longitude'],
                    'wind_force': forces.get('wind', {}).get('magnitude', 0),
                    'wind_speed': state.get('environment', {}).get('windSpeed', 0),
                    'depth': state.get('environment', {}).get('depth', 0),
                    'speed': state.get('boat', {}).get('speed', 0),
                })
        except:
            pass
        time.sleep(SAMPLE_INTERVAL)

    # Stop
    send_command(token, "stop")

    # Analyze
    if not samples:
        print("✗ No samples collected!")
        return None

    final = samples[-1]
    lat_change = final['lat'] - start_lat
    lon_change = final['lon'] - start_lon
    north_movement = lat_change / 0.000009  # meters

    max_speed = max(s['speed'] for s in samples)
    avg_wind_force = sum(s['wind_force'] for s in samples) / len(samples)

    print(f"\n[RESULTS]")
    print(f"  Movement North: {north_movement:.1f}m")
    print(f"  Max Speed: {max_speed:.3f} m/s ({max_speed * 1.94384:.2f} kn)")
    print(f"  Avg Wind Force: {avg_wind_force:.1f}N")
    print(f"  Wind Speed Used: {final['wind_speed']}kn")
    print(f"  Depth Used: {final['depth']}m")

    return {
        'wind_speed': wind_speed,
        'depth': depth,
        'movement_north': north_movement,
        'max_speed': max_speed,
        'avg_wind_force': avg_wind_force,
        'samples': len(samples),
    }


def main():
    print("\n" + "="*60)
    print("QUICK VALIDATION TEST")
    print("Testing config application with 4 corner cases")
    print("="*60)

    token = get_auth_token()
    if not token:
        print("✗ Failed to authenticate")
        return 1
    print("✓ Authenticated")

    results = []
    for wind, depth, description in TEST_CASES:
        result = run_single_test(token, wind, depth, description)
        if result:
            results.append(result)

    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)

    if len(results) < 4:
        print(f"✗ Only {len(results)}/4 tests completed")
        return 1

    print(f"\n{'Wind':<6} {'Depth':<6} {'Movement':<12} {'Max Speed':<12} {'Avg Force':<12}")
    print("-" * 50)
    for r in results:
        print(f"{r['wind_speed']:>4}kn {r['depth']:>4}m  {r['movement_north']:>8.1f}m   "
              f"{r['max_speed']:>8.3f}m/s  {r['avg_wind_force']:>8.1f}N")

    # Check differentiation
    forces = [r['avg_wind_force'] for r in results]
    force_ratio = max(forces) / min(forces) if min(forces) > 0 else 0

    print(f"\n[VALIDATION CHECK]")
    print(f"  Force ratio (25kn/4kn): {force_ratio:.1f}x")
    print(f"  Expected ratio: ~39x (25²/4² = 39.06)")

    if force_ratio > 30:
        print("  ✓ PASS - Wind force scales correctly with wind speed")
    else:
        print("  ✗ FAIL - Wind force not scaling correctly")
        return 1

    print("\n✓ Validation complete - config changes are being applied correctly!")
    return 0


if __name__ == '__main__':
    exit(main())

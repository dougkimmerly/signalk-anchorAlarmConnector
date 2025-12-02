#!/usr/bin/env python3
"""
V2 Simulation Test Script
Runs a single test cycle: reset, observe movement for 30 seconds, report results
"""

import json
import time
import urllib.request
import urllib.error
import sys

BASE_URL = "http://localhost:80"

def get_auth_token():
    """Get authentication token"""
    try:
        url = f"{BASE_URL}/signalk/v1/auth/login"
        data = json.dumps({"username": "admin", "password": "signalk"}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read()).get('token')
    except Exception as e:
        print(f"Auth error: {e}")
        return None

def get_position():
    """Get current boat position"""
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/position/value"
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read())
    except:
        return None

def get_speed():
    """Get current boat speed"""
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/speedOverGround/value"
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.loads(response.read())
    except:
        return None

def get_simulation_state(token):
    """Get V2 simulation state"""
    try:
        url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/simulation/state"
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"Simulation state error: {e}")
        return None

def run_test(test_num):
    """Run a single test"""
    print(f"\n{'='*50}")
    print(f"  TEST {test_num}")
    print(f"{'='*50}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Get auth token
    token = get_auth_token()
    if not token:
        print("ERROR: Could not get auth token")
        return None

    # Get initial position
    initial_pos = get_position()
    if not initial_pos:
        print("ERROR: Could not get initial position")
        return None

    print(f"\nInitial position: {initial_pos['latitude']:.6f}, {initial_pos['longitude']:.6f}")

    # Collect samples over 30 seconds
    samples = []
    print("\nCollecting samples over 30 seconds...")
    for i in range(6):
        time.sleep(5)
        pos = get_position()
        spd = get_speed()
        if pos and spd is not None:
            samples.append({
                'sample': i + 1,
                'latitude': pos['latitude'],
                'longitude': pos['longitude'],
                'speed': spd
            })
            print(f"  Sample {i+1}: lat={pos['latitude']:.6f}, speed={spd:.4f} m/s")

    # Get final simulation state
    sim_state = get_simulation_state(token)

    # Calculate results
    if len(samples) >= 2:
        lat_change = samples[-1]['latitude'] - samples[0]['latitude']
        direction = "NORTH" if lat_change > 0 else "SOUTH" if lat_change < 0 else "STATIONARY"
        distance_m = abs(lat_change) / 0.000009  # convert to meters
        avg_speed = sum(s['speed'] for s in samples) / len(samples)
        final_speed = samples[-1]['speed']

        print(f"\n--- Results ---")
        print(f"Direction: {direction}")
        print(f"Latitude change: {lat_change:.8f} ({distance_m:.1f}m)")
        print(f"Average speed: {avg_speed:.4f} m/s")
        print(f"Final speed: {final_speed:.4f} m/s")

        if sim_state:
            print(f"\n--- Simulation State ---")
            print(f"Wind: {sim_state['environment']['windSpeed']} kn from {sim_state['environment']['windDirection']}°")
            print(f"Wind Force: {sim_state['forces']['wind']['magnitude']:.1f} N")
            print(f"Drag Force: {sim_state['forces']['waterDrag']['magnitude']:.1f} N")
            print(f"Heading: {sim_state['boat']['heading']:.2f}°")

        return {
            'test_num': test_num,
            'direction': direction,
            'lat_change': lat_change,
            'distance_m': distance_m,
            'avg_speed': avg_speed,
            'final_speed': final_speed,
            'samples': samples,
            'sim_state': sim_state
        }

    return None

if __name__ == '__main__':
    test_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    result = run_test(test_num)
    if result:
        print(f"\n✓ Test {test_num} completed successfully")
    else:
        print(f"\n✗ Test {test_num} failed")

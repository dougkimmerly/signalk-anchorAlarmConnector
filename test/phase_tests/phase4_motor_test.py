#!/usr/bin/env python3
"""
Phase 4 Motor Force Testing
Tests how motor thrust affects boat movement toward/away from anchor
"""

import json
import time
import urllib.request
import urllib.error
import sys
import math

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

def get_heading():
    """Get current boat heading in degrees"""
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/headingTrue/value"
        with urllib.request.urlopen(url, timeout=5) as response:
            rad = json.loads(response.read())
            return rad * 180 / math.pi
    except:
        return None

def get_simulation_state(token):
    """Get simulation state including motor forces"""
    try:
        url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/simulation/state"
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read())
    except:
        return None

def send_motor_command(command, token):
    """Send motor command to simulator"""
    try:
        url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/{command}"
        req = urllib.request.Request(url, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            resp_text = response.read().decode()
            try:
                return json.loads(resp_text)
            except:
                return resp_text
    except Exception as e:
        print(f"  Error sending command: {e}")
        return None

def send_throttle_command(throttle, token):
    """Set motor throttle (0.0 to 1.0)"""
    try:
        url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/motorthrottle"
        data = json.dumps({"throttle": throttle}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            resp_text = response.read().decode()
            try:
                return json.loads(resp_text)
            except:
                return resp_text
    except Exception as e:
        print(f"  Error setting throttle: {e}")
        return None

def run_motor_test(test_name, description, command, duration, analysis_fn):
    """Run a motor test"""
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")
    print(f"Description: {description}\n")

    token = get_auth_token()
    if not token:
        print("✗ Could not get auth token")
        return None

    # Get initial state
    initial_pos = get_position()
    initial_speed = get_speed()
    initial_heading = get_heading()

    if initial_pos is None or initial_speed is None:
        print("✗ Could not get initial state")
        return None

    initial_lat = initial_pos['latitude']
    initial_lon = initial_pos['longitude']
    initial_heading_norm = initial_heading % 360 if initial_heading else 0

    print(f"Initial state:")
    print(f"  Position: {initial_lat:.6f}, {initial_lon:.6f}")
    print(f"  Speed: {initial_speed:.4f} m/s")
    print(f"  Heading: {initial_heading_norm:.1f}°\n")

    # Send motor command
    print(f"Sending command: {command}")
    result = send_motor_command(command, token)
    print(f"Result: {result}\n")

    # Collect samples over duration
    print(f"Collecting samples over {duration} seconds...\n")

    samples = []
    start_time = time.time()

    try:
        while time.time() - start_time < duration:
            elapsed = time.time() - start_time

            pos = get_position()
            spd = get_speed()
            hdg = get_heading()
            sim_state = get_simulation_state(token)

            if pos and spd is not None:
                # Calculate distance from initial position
                lat_delta = (pos['latitude'] - initial_lat) / 0.000009  # Convert to meters

                samples.append({
                    'time': elapsed,
                    'latitude': pos['latitude'],
                    'longitude': pos['longitude'],
                    'speed': spd,
                    'heading': (hdg % 360) if hdg else 0,
                    'distance_from_start': lat_delta,
                    'motor_force': sim_state['forces']['motor']['magnitude'] if sim_state else 0,
                    'total_force': sim_state['forces']['total']['magnitude'] if sim_state else 0,
                })

                # Print every 5 seconds
                if int(elapsed) % 5 == 0 or len(samples) == 1:
                    print(f"[{elapsed:6.1f}s] Speed: {spd:5.2f} m/s | Motor: {samples[-1]['motor_force']:7.1f} N | "
                          f"Distance: {lat_delta:6.1f}m")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")

    # Send stop command
    print(f"\n\nStopping motor...")
    send_motor_command('motorstop', token)

    # Get final simulation state
    sim_state = get_simulation_state(token)

    # Analyze results
    final_lat = samples[-1]['latitude'] if samples else initial_lat
    final_lon = samples[-1]['longitude'] if samples else initial_lon
    final_speed = samples[-1]['speed'] if samples else 0
    final_distance = samples[-1]['distance_from_start'] if samples else 0

    print(f"\n--- Final State ---")
    print(f"Position: {final_lat:.6f}, {final_lon:.6f}")
    print(f"Distance from start: {final_distance:.1f}m")
    print(f"Final speed: {final_speed:.4f} m/s")

    if sim_state:
        print(f"\n--- Simulation State ---")
        print(f"Motor force: {sim_state['forces']['motor']['magnitude']:.1f} N")
        print(f"Total force: {sim_state['forces']['total']['magnitude']:.1f} N")
        print(f"Wind force: {sim_state['forces']['wind']['magnitude']:.1f} N")
        print(f"Drag force: {sim_state['forces']['waterDrag']['magnitude']:.1f} N")

    # Run analysis specific to this test
    result = analysis_fn(test_name, samples, final_distance, final_speed, sim_state)

    return {
        'test_name': test_name,
        'command': command,
        'duration': duration,
        'initial_position': (initial_lat, initial_lon),
        'final_position': (final_lat, final_lon),
        'distance_moved': final_distance,
        'final_speed': final_speed,
        'samples': samples,
        'sim_state': sim_state,
        'analysis': result
    }

# Test 1: Motor Forward (toward anchor)
def analyze_motor_forward(test_name, samples, distance, final_speed, sim_state):
    """Analyze motor forward results"""
    print(f"\n--- Expected Behavior ---")
    print(f"Motor forward: 500N thrust along boat heading")
    print(f"Expected: Boat accelerates toward anchor, moving away from current wind push")

    # Calculate average motor force
    avg_motor_force = sum(s['motor_force'] for s in samples) / len(samples) if samples else 0

    print(f"\nAverage motor force: {avg_motor_force:.1f} N")

    if avg_motor_force > 400:
        print(f"✓ PASS: Motor force present ({avg_motor_force:.1f}N)")
        return True
    else:
        print(f"✗ FAIL: Motor force too low ({avg_motor_force:.1f}N)")
        return False

result1 = run_motor_test(
    "MOTOR FORWARD (Retrieval Assist)",
    "Motor provides 500N thrust along heading - simulates pulling boat toward anchor",
    "motorforward",
    30,
    analyze_motor_forward
)

time.sleep(2)

# Test 2: Motor Backward (away from anchor)
def analyze_motor_backward(test_name, samples, distance, final_speed, sim_state):
    """Analyze motor backward results"""
    print(f"\n--- Expected Behavior ---")
    print(f"Motor backward: 300N thrust opposite to heading")
    print(f"Expected: Boat accelerates away from anchor, supplementing wind force")

    # Calculate average motor force
    avg_motor_force = sum(s['motor_force'] for s in samples) / len(samples) if samples else 0

    print(f"\nAverage motor force: {avg_motor_force:.1f} N")

    if avg_motor_force > 250:
        print(f"✓ PASS: Motor backward force present ({avg_motor_force:.1f}N)")
        return True
    else:
        print(f"✗ FAIL: Motor backward force too low ({avg_motor_force:.1f}N)")
        return False

result2 = run_motor_test(
    "MOTOR BACKWARD (Deployment Assist)",
    "Motor provides 300N thrust opposite to heading - simulates pushing boat away for anchor deployment",
    "motorbackward",
    30,
    analyze_motor_backward
)

time.sleep(2)

# Test 3: Throttle Control
print(f"\n{'='*70}")
print(f"TEST: THROTTLE CONTROL")
print(f"{'='*70}")
print(f"Description: Test motor throttle scaling from 0.0 to 1.0\n")

token = get_auth_token()
if token:
    throttle_results = []

    # Start motor forward with initial throttle of 1.0
    print(f"Starting motor forward for throttle testing...")
    send_motor_command('motorforward', token)
    time.sleep(2)

    for throttle in [0.25, 0.5, 0.75, 1.0]:
        print(f"Setting throttle to {throttle}...")
        send_throttle_command(throttle, token)

        # Let throttle settle
        time.sleep(2)

        # Collect sample
        pos = get_position()
        spd = get_speed()
        sim_state = get_simulation_state(token)

        if sim_state:
            motor_force = sim_state['forces']['motor']['magnitude']
            throttle_results.append({
                'throttle': throttle,
                'motor_force': motor_force,
                'speed': spd or 0
            })
            print(f"  Throttle {throttle}: Motor force = {motor_force:.1f} N, Speed = {spd:.2f} m/s")

        time.sleep(1)

    # Stop motor
    send_motor_command('motorstop', token)

    print(f"\n--- Throttle Control Analysis ---")
    if throttle_results:
        # Check if force scales linearly
        forces = [r['motor_force'] for r in throttle_results]
        expected_ratio = 0.25 / 1.0
        actual_ratio = forces[0] / forces[-1] if forces[-1] > 0 else 0

        print(f"Force at 25% throttle: {forces[0]:.1f} N")
        print(f"Force at 100% throttle: {forces[-1]:.1f} N")
        print(f"Scaling ratio (25%/100%): {actual_ratio:.2f} (expected ~0.25)")

        if 0.2 < actual_ratio < 0.3:
            print("✓ PASS: Throttle control works correctly (linear scaling)")
        else:
            print("✗ FAIL: Throttle scaling not linear")

# Summary
print(f"\n{'='*70}")
print(f"  PHASE 4 TEST SUMMARY")
print(f"{'='*70}\n")

results = [
    (result1, "Motor forward"),
    (result2, "Motor backward"),
]

for result, name in results:
    if result:
        analysis = result.get('analysis', False)
        status = "✓ PASS" if analysis else "✗ FAIL"
        print(f"{status} - {name}: avg motor force, distance={result['distance_moved']:.1f}m")

print(f"\nNotes:")
print(f"- Motor forward provides 500N thrust toward anchor (retrieval assist)")
print(f"- Motor backward provides 300N thrust away from anchor (deployment assist)")
print(f"- Throttle control scales force from 0.0 (off) to 1.0 (full)")
print(f"- Motor thrust direction follows boat heading, not anchor direction")
print(f"- Combined with wind and drag, motor creates realistic boat dynamics")

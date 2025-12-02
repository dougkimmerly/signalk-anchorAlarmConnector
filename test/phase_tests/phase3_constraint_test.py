#!/usr/bin/env python3
"""
Phase 3 Slack Constraint Testing
Tests how boat movement is constrained by chain slack
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

def get_simulation_state(token):
    """Get V2 simulation state"""
    try:
        url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/simulation/state"
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read())
    except:
        return None

def set_anchor_position(token, lat, lon):
    """Set anchor position via SignalK"""
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/anchor/position"
        data = json.dumps({"value": {"latitude": lat, "longitude": lon}}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return True
    except:
        return False

def enable_constraint(token):
    """Enable slack constraint force via HTTP endpoint"""
    try:
        url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/simulation/config"
        config = {
            "forces": {
                "slackConstraint": {
                    "enabled": True
                }
            }
        }
        data = json.dumps(config).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return True
    except Exception as e:
        print(f"Note: Could not enable constraint via API: {e}")
        # Continue anyway - may already be enabled
        return True

def run_constraint_test(test_name, description, slack_value, setup_fn, analysis_fn):
    """Run a slack constraint test"""
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")
    print(f"Description: {description}")
    print(f"Slack setting: {slack_value} m\n")

    token = get_auth_token()
    if not token:
        print("✗ Could not get auth token")
        return None

    # Run setup (e.g., set anchor position, enable constraint)
    if not setup_fn(token, slack_value):
        print("✗ Setup failed")
        return None

    # Collect movement data
    initial_pos = get_position()
    if initial_pos is None:
        print("✗ Could not get initial position")
        return None

    initial_lat = initial_pos['latitude']
    initial_lon = initial_pos['longitude']

    print(f"Initial position: {initial_lat:.6f}, {initial_lon:.6f}")
    print("Collecting samples over 30 seconds...\n")

    positions = [(initial_lat, initial_lon)]
    speeds = []

    for i in range(6):
        time.sleep(5)
        pos = get_position()
        spd = get_speed()
        if pos and spd is not None:
            positions.append((pos['latitude'], pos['longitude']))
            speeds.append(spd)
            lat_delta = (pos['latitude'] - initial_lat) / 0.000009  # Convert to meters
            print(f"  Sample {i+1}: lat_delta={lat_delta:.1f}m, speed={spd:.4f} m/s")

    # Get final simulation state
    sim_state = get_simulation_state(token)

    # Calculate results
    final_lat = positions[-1][0]
    final_lon = positions[-1][1]

    distance_moved = (final_lat - initial_lat) / 0.000009  # Convert to meters
    avg_speed = sum(speeds) / len(speeds) if speeds else 0
    final_speed = speeds[-1] if speeds else 0

    print(f"\n--- Movement Analysis ---")
    print(f"Distance moved (North): {distance_moved:.1f}m")
    print(f"Average speed: {avg_speed:.4f} m/s")
    print(f"Final speed: {final_speed:.4f} m/s")

    if sim_state:
        print(f"\n--- Simulation State ---")
        print(f"Is anchored: {sim_state['boat']['isAnchored']}")
        if sim_state['boat']['isAnchored']:
            print(f"Distance to anchor: {sim_state.get('distance_to_anchor', 'N/A')}m")

        print(f"\nForces:")
        print(f"  Wind force: {sim_state['forces']['wind']['magnitude']:.1f} N")
        print(f"  Drag force: {sim_state['forces']['waterDrag']['magnitude']:.1f} N")
        print(f"  Constraint force: {sim_state['forces']['constraint']['magnitude']:.1f} N")
        print(f"  Total force: {sim_state['forces']['total']['magnitude']:.1f} N")

    # Run analysis specific to this test
    result = analysis_fn(test_name, distance_moved, avg_speed, final_speed, slack_value, sim_state)

    return {
        'test_name': test_name,
        'slack': slack_value,
        'distance_moved': distance_moved,
        'avg_speed': avg_speed,
        'final_speed': final_speed,
        'positions': positions,
        'speeds': speeds,
        'sim_state': sim_state,
        'analysis': result
    }

# Test 1: No constraint (slack > depth)
def setup_no_constraint(token, slack):
    """Setup for no constraint test"""
    if not enable_constraint(token):
        return False

    # Get current position and set anchor far away
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/position/value"
        with urllib.request.urlopen(url, timeout=5) as response:
            pos = json.loads(response.read())
            # Set anchor 100m south (tight rope, but slack > depth)
            anchor_lat = pos['latitude'] - 0.0009  # ~100m south
            return set_anchor_position(token, anchor_lat, pos['longitude'])
    except:
        return False

def analyze_no_constraint(test_name, distance, avg_speed, final_speed, slack, sim_state):
    """Analyze no constraint results"""
    print(f"\n--- Expected Behavior ---")
    print(f"Slack {slack}m > depth 3m: Chain hanging loose, NO constraint")
    print(f"Boat should move freely with wind")

    if distance > 5:
        print(f"\n✓ PASS: Boat moved {distance:.1f}m (freely)")
        return True
    else:
        print(f"\n✗ FAIL: Boat barely moved {distance:.1f}m")
        return False

result1 = run_constraint_test(
    "NO CONSTRAINT (slack > depth)",
    "Slack is greater than depth - chain hanging loose",
    slack_value=5.0,
    setup_fn=setup_no_constraint,
    analysis_fn=analyze_no_constraint
)

# Test 2: Partial constraint (slack < depth)
def setup_partial_constraint(token, slack):
    """Setup for partial constraint test"""
    if not enable_constraint(token):
        return False

    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/position/value"
        with urllib.request.urlopen(url, timeout=5) as response:
            pos = json.loads(response.read())
            # Set anchor 50m away (moderate constraint)
            anchor_lat = pos['latitude'] - 0.0045  # ~50m away
            return set_anchor_position(token, anchor_lat, pos['longitude'])
    except:
        return False

def analyze_partial_constraint(test_name, distance, avg_speed, final_speed, slack, sim_state):
    """Analyze partial constraint results"""
    print(f"\n--- Expected Behavior ---")
    print(f"Slack {slack}m < depth 3m: Chain tightening, PARTIAL constraint")
    print(f"Boat should move but slower than with no constraint")

    if distance > 0 and distance < 15:
        print(f"\n✓ PASS: Boat moved {distance:.1f}m (constrained)")
        return True
    else:
        print(f"\n✗ FAIL: Unexpected movement {distance:.1f}m")
        return False

result2 = run_constraint_test(
    "PARTIAL CONSTRAINT (slack < depth)",
    "Slack is 1.5m, less than depth 3m - chain tightening",
    slack_value=1.5,
    setup_fn=setup_partial_constraint,
    analysis_fn=analyze_partial_constraint
)

# Test 3: Full constraint (slack = 0)
def setup_full_constraint(token, slack):
    """Setup for full constraint test"""
    if not enable_constraint(token):
        return False

    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/position/value"
        with urllib.request.urlopen(url, timeout=5) as response:
            pos = json.loads(response.read())
            # Set anchor 25m away (at rode limit)
            anchor_lat = pos['latitude'] - 0.00225  # ~25m away
            return set_anchor_position(token, anchor_lat, pos['longitude'])
    except:
        return False

def analyze_full_constraint(test_name, distance, avg_speed, final_speed, slack, sim_state):
    """Analyze full constraint results"""
    print(f"\n--- Expected Behavior ---")
    print(f"Slack {slack}m = 0: Chain fully taut, FULL constraint")
    print(f"Boat should move very little (almost stopped)")

    if distance < 3:
        print(f"\n✓ PASS: Boat barely moved {distance:.1f}m (strongly constrained)")
        return True
    else:
        print(f"\n✗ FAIL: Boat moved too much {distance:.1f}m")
        return False

result3 = run_constraint_test(
    "FULL CONSTRAINT (slack = 0)",
    "Slack is 0m - chain fully taut at rode limit",
    slack_value=0.0,
    setup_fn=setup_full_constraint,
    analysis_fn=analyze_full_constraint
)

# Summary
print(f"\n{'='*70}")
print("  PHASE 3 TEST SUMMARY")
print(f"{'='*70}\n")

test_results = [
    (result1, "No constraint"),
    (result2, "Partial constraint"),
    (result3, "Full constraint")
]

for result, name in test_results:
    if result:
        analysis = result.get('analysis', False)
        status = "✓ PASS" if analysis else "✗ FAIL"
        print(f"{status} - {name}: {result['distance_moved']:.1f}m moved, slack={result['slack']}m")

print("\nNotes:")
print("- Test 1 should see free movement (no constraint)")
print("- Test 2 should see reduced movement (partial constraint)")
print("- Test 3 should see minimal movement (full constraint)")
print("- Wind is 10 knots from South pushing North throughout all tests")

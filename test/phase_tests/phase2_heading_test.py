#!/usr/bin/env python3
"""
Phase 2 Heading Behavior Test
Tests how boat heading responds to wind and anchor forces
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
        return None

def get_heading():
    """Get current boat heading"""
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/headingTrue/value"
        with urllib.request.urlopen(url, timeout=5) as response:
            rad = json.loads(response.read())
            return rad * 180 / 3.14159265359  # Convert radians to degrees
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
    except Exception as e:
        print(f"Failed to set anchor: {e}")
        return False

def normalize_angle(angle):
    """Normalize angle to 0-360"""
    while angle < 0:
        angle += 360
    while angle >= 360:
        angle -= 360
    return angle

def angle_diff(a1, a2):
    """Calculate smallest angle difference"""
    diff = abs(a1 - a2)
    if diff > 180:
        diff = 360 - diff
    return diff

def run_heading_test(test_name, description, setup_fn, expected_behavior):
    """Run a heading test"""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")
    print(f"Description: {description}")
    print(f"Expected: {expected_behavior}\n")

    token = get_auth_token()
    if not token:
        print("✗ Could not get auth token")
        return None

    # Run setup (e.g., set anchor position)
    if not setup_fn(token):
        print("✗ Setup failed")
        return None

    # Collect heading data
    initial_heading = get_heading()
    if initial_heading is None:
        print("✗ Could not get initial heading")
        return None

    initial_heading = normalize_angle(initial_heading)
    print(f"Initial heading: {initial_heading:.1f}°")

    headings = [initial_heading]
    print("Collecting samples over 30 seconds...\n")

    for i in range(6):
        time.sleep(5)
        heading = get_heading()
        if heading is not None:
            heading = normalize_angle(heading)
            headings.append(heading)
            print(f"  Sample {i+1}: {heading:.1f}°")

    # Get simulation state
    sim_state = get_simulation_state(token)

    # Analyze results
    final_heading = headings[-1]
    heading_change = angle_diff(initial_heading, final_heading)

    print(f"\n--- Analysis ---")
    print(f"Initial heading: {initial_heading:.1f}°")
    print(f"Final heading: {final_heading:.1f}°")
    print(f"Total change: {heading_change:.1f}°")

    if sim_state:
        print(f"\n--- Simulation State ---")
        print(f"Boat position: {sim_state['boat']['latitude']:.6f}, {sim_state['boat']['longitude']:.6f}")
        print(f"Wind: {sim_state['environment']['windSpeed']} kn from {sim_state['environment']['windDirection']}°")
        print(f"Is Anchored: {sim_state['boat']['isAnchored']}")
        if sim_state['boat']['isAnchored']:
            anchor_lat = sim_state['boat']['anchorLatitude']
            anchor_lon = sim_state['boat']['anchorLongitude']
            boat_lat = sim_state['boat']['latitude']
            boat_lon = sim_state['boat']['longitude']

            # Calculate bearing to anchor (simple approximation)
            dlat = anchor_lat - boat_lat
            dlon = anchor_lon - boat_lon
            import math
            bearing_rad = math.atan2(dlon, dlat)
            bearing_deg = bearing_rad * 180 / math.pi
            bearing_deg = normalize_angle(bearing_deg)

            dist = math.sqrt(dlat*dlat/0.000009**2 + dlon*dlon/0.0000125**2)

            print(f"Anchor: {anchor_lat:.6f}, {anchor_lon:.6f}")
            print(f"Distance to anchor: {dist:.1f}m")
            print(f"Bearing to anchor: {bearing_deg:.1f}°")

        print(f"\nTorque values:")
        print(f"  Wind torque: {sim_state['forces']['torque'].get('wind', 'N/A')}")
        print(f"  Anchor torque: {sim_state['forces']['torque'].get('anchor', 'N/A')}")
        print(f"  Total torque: {sim_state['forces']['torque']['total']:.6f}")
        print(f"  Tension factor: {sim_state['forces']['torque'].get('tensionFactor', 'N/A')}")

    return {
        'test_name': test_name,
        'initial_heading': initial_heading,
        'final_heading': final_heading,
        'heading_change': heading_change,
        'headings': headings,
        'sim_state': sim_state
    }

# Test 1: Free boat weathervane (no anchor set)
def setup_free_boat(token):
    """No anchor setup needed for free boat test"""
    return True

result1 = run_heading_test(
    "FREE BOAT WEATHERVANE",
    "Boat with no anchor should point into wind (weathervane effect)",
    setup_free_boat,
    "Heading rotates toward wind source (180° if wind from South)"
)

# Test 2: Anchored boat with tight chain
def setup_anchored_tight(token):
    """Set anchor very close to boat (tight chain)"""
    # Get current position
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/position/value"
        with urllib.request.urlopen(url, timeout=5) as response:
            pos = json.loads(response.read())
            current_lat = pos['latitude']
            current_lon = pos['longitude']

            # Set anchor just north of current position (tight chain)
            anchor_lat = current_lat + 0.0001  # ~11 meters north
            anchor_lon = current_lon

            return set_anchor_position(token, anchor_lat, anchor_lon)
    except:
        return False

result2 = run_heading_test(
    "ANCHORED WITH TIGHT CHAIN",
    "Boat with anchor close (tight chain) should point toward anchor",
    setup_anchored_tight,
    "Heading rotates toward anchor (~0° if anchor is North), anchor dominates wind"
)

# Test 3: Anchored boat with slack chain
def setup_anchored_slack(token):
    """Set anchor far from boat (slack chain)"""
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/position/value"
        with urllib.request.urlopen(url, timeout=5) as response:
            pos = json.loads(response.read())
            current_lat = pos['latitude']
            current_lon = pos['longitude']

            # Set anchor far from current position (lots of slack)
            anchor_lat = current_lat + 0.001  # ~111 meters north
            anchor_lon = current_lon

            return set_anchor_position(token, anchor_lat, anchor_lon)
    except:
        return False

result3 = run_heading_test(
    "ANCHORED WITH SLACK CHAIN",
    "Boat with anchor far (slack chain) should show wind influence",
    setup_anchored_slack,
    "Heading between wind source and anchor, wind has more influence"
)

# Summary
print(f"\n{'='*60}")
print("  PHASE 2 TEST SUMMARY")
print(f"{'='*60}\n")

if result1:
    print(f"Test 1 - Free boat: {result1['heading_change']:.1f}° change")
    if result1['heading_change'] > 5:
        print("  ✓ Heading rotated (weathervane detected)")
    else:
        print("  ✗ Heading barely changed")

if result2:
    print(f"\nTest 2 - Anchored tight: {result2['heading_change']:.1f}° change")
    if result2['heading_change'] > 5:
        print("  ✓ Heading rotated (anchor influence detected)")
    else:
        print("  ✗ Heading barely changed")

if result3:
    print(f"\nTest 3 - Anchored slack: {result3['heading_change']:.1f}° change")
    if result3['heading_change'] > 5:
        print("  ✓ Heading rotated (wind influence with slack)")
    else:
        print("  ✗ Heading barely changed")

#!/usr/bin/env python3
"""
Test autoDrop and autoRetrieve with settling time between them.
- Drop timeout: 3 minutes (180s), but detects when drop completes
- Settling time: 20 seconds
- Retrieve timeout: 2 minutes (120s)
"""

import urllib.request
import json
import time
import math

BASE_URL = "http://localhost:80"

# Test parameters
DROP_TIMEOUT = 240      # 4 minutes max for drop
SETTLE_TIME = 20        # 20 seconds settling
RETRIEVE_TIMEOUT = 240  # 4 minutes max for retrieve

def get_token():
    url = f"{BASE_URL}/signalk/v1/auth/login"
    data = json.dumps({"username": "admin", "password": "signalk"}).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read()).get('token')

def get_rode(token):
    url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/anchor/rodeDeployed/value"
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read())

def get_scope(token):
    url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/anchor/scope/value"
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read())

def get_sim_state(token):
    url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/simulation/state"
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read())

def get_chain_direction(token):
    url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/anchor/chainDirection/value"
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read())

def send_cmd(token, cmd):
    url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/anchor/command"
    data = json.dumps({"value": cmd}).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='PUT')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode())

def configure_env(token, wind, depth):
    url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/simulation/config"
    data = json.dumps({
        "wind": {"initialSpeed": wind, "initialDirection": 180},
        "environment": {"depth": depth}
    }).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='PUT')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.loads(response.read())

def calc_distance(state):
    if not state['boat'].get('anchorLatitude'):
        return None
    lat1, lon1 = state['boat']['latitude'], state['boat']['longitude']
    lat2, lon2 = state['boat']['anchorLatitude'], state['boat']['anchorLongitude']
    dlat = (lat2 - lat1) / 0.000009
    dlon = (lon2 - lon1) / 0.0000125
    return math.sqrt(dlat**2 + dlon**2)

def print_status(i, rode, state, extra=""):
    dist = calc_distance(state)
    slack = state['forces']['constraint'].get('slack', 0)
    speed = state['boat']['speed']
    constrained = state['forces']['constraint'].get('isConstrained', False)
    motor = state['forces']['motor'].get('magnitude', 0)

    if dist:
        c = "C" if constrained else " "
        print(f"[{i:3d}s] rode={rode:5.1f}m  dist={dist:5.1f}m  slack={slack:6.1f}m  speed={speed:.2f}m/s  motor={motor:6.0f}N {c} {extra}")
    else:
        print(f"[{i:3d}s] rode={rode:5.1f}m  (no anchor) {extra}")

token = get_token()

# Configure 8kn wind, 3m depth
print("=== CONFIGURING: 8kn wind, 3m depth ===")
configure_env(token, 8, 3)
time.sleep(1)

# Check initial state
rode = get_rode(token)
state = get_sim_state(token)
print(f"Initial: rode={rode}m, isAnchored={state['boat']['isAnchored']}")

# Start autoDrop
print(f"\n=== AUTODROP (max {DROP_TIMEOUT}s, stops when chain direction goes idle) ===")
send_cmd(token, 'autoDrop')

last_rode = 0
idle_count = 0
for i in range(DROP_TIMEOUT):
    time.sleep(1)
    rode = get_rode(token)
    state = get_sim_state(token)
    chain_dir = get_chain_direction(token)

    extra = f"[{chain_dir}]" if chain_dir else ""
    print_status(i+1, rode, state, extra)

    # Detect drop completion: chain direction goes idle and rode stopped changing
    if chain_dir == 'idle' and rode == last_rode:
        idle_count += 1
        if idle_count >= 3:  # 3 consecutive idle readings
            print(f"\n✓ Drop complete detected (chain idle, rode stable at {rode}m)")
            break
    else:
        idle_count = 0
    last_rode = rode

# Stop deployment
print("\n=== STOPPING DEPLOYMENT ===")
send_cmd(token, 'stop')
time.sleep(2)

rode = get_rode(token)
state = get_sim_state(token)
dist = calc_distance(state)
print(f"After drop: rode={rode:.1f}m, dist={dist:.1f}m" if dist else f"After drop: rode={rode}m")

# Wait for settling
print(f"\n=== WAITING {SETTLE_TIME}s FOR SETTLING ===")
for i in range(SETTLE_TIME):
    time.sleep(1)
    rode = get_rode(token)
    state = get_sim_state(token)
    print_status(i+1, rode, state)

# Now test autoRetrieve
print(f"\n=== AUTORETRIEVE (max {RETRIEVE_TIMEOUT}s) ===")
send_cmd(token, 'autoRetrieve')

for i in range(RETRIEVE_TIMEOUT):
    time.sleep(1)
    rode = get_rode(token)
    state = get_sim_state(token)
    chain_dir = get_chain_direction(token)

    extra = f"[{chain_dir}]" if chain_dir else ""
    print_status(i+1, rode, state, extra)

    if rode <= 0.5:
        print("\n✓ Retrieval complete!")
        break

    # Detect 2m safety stop (rode at 2m and chain not moving up)
    if rode <= 2.0 and chain_dir in ['idle', 'free fall']:
        print(f"\n✓ Reached 2m safety stop (chainDirection={chain_dir})!")
        break

print("\n=== FINAL ===")
send_cmd(token, 'stop')
rode = get_rode(token)
print(f"Final rode: {rode}m")

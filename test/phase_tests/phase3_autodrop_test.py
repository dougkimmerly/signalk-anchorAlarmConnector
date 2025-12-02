#!/usr/bin/env python3
"""
Phase 3 Slack Constraint Testing with AutoDrop
Tests boat constraint behavior as anchor is deployed with autoDrop command
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

def send_anchor_command(token, command):
    """Send command to anchor subsystem"""
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/anchor/command"
        data = json.dumps({"value": command}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            resp_data = json.loads(response.read())
            return resp_data.get('state') or 'command sent'
    except Exception as e:
        print(f"  Error sending command: {e}")
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

def get_rode_deployed():
    """Get rode deployed"""
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/anchor/rodeDeployed/value"
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

# Get auth token
token = get_auth_token()
if not token:
    print("✗ Could not get auth token")
    sys.exit(1)

print("="*70)
print("  PHASE 3: SLACK CONSTRAINT WITH AUTODROP")
print("="*70)
print()
print("This test deploys the anchor using autoDrop and monitors")
print("slack constraint force at each hold point.\n")

# Step 1: Get current boat position (anchor will be set by autoDrop at boat position)
print("Step 1: Getting current boat position...")
pos = get_position()
if not pos:
    print("✗ Could not get position")
    sys.exit(1)

current_lat = pos['latitude']
current_lon = pos['longitude']

print(f"✓ Boat position: {current_lat:.6f}, {current_lon:.6f}")
print(f"  Anchor will be deployed at this position\n")

# Step 2: Send autoDrop command
print("Step 2: Sending autoDrop command...")
result = send_anchor_command(token, "autoDrop")
print(f"✓ autoDrop command sent: {result}\n")

# Step 3: Monitor deployment and slack constraint
print("Step 3: Monitoring anchor deployment and slack constraint\n")
print("Expected deployment timeline:")
print("  0s:  Drop to seabed, 0m slack (hold 2s)")
print("  2s:  At 40% scope (~268m rode), anchor digging (hold 30s)")
print("  32s: At 80% scope (~536m rode), anchor fully dug (hold 75s)")
print("  107s: At 100% scope (~670m rode), fully deployed\n")

deployment_phases = [
    {"name": "Initial drop (0-2s)", "expected_rode": 0, "expected_slack": 0, "duration": 3},
    {"name": "40% scope digging (30-32s)", "expected_rode": 268, "expected_slack": "varies", "duration": 35},
    {"name": "80% scope dug (75-107s)", "expected_rode": 536, "expected_slack": "varies", "duration": 35},
    {"name": "100% fully deployed (107s+)", "expected_rode": 670, "expected_slack": "varies", "duration": 30}
]

samples = []
start_time = time.time()

try:
    for i in range(150):  # 150 samples * 1s = 150 seconds total
        elapsed = time.time() - start_time

        pos = get_position()
        spd = get_speed()
        rode = get_rode_deployed()
        sim_state = get_simulation_state(token)

        if pos and spd is not None and rode is not None:
            samples.append({
                'time': elapsed,
                'latitude': pos['latitude'],
                'longitude': pos['longitude'],
                'speed': spd,
                'rode': rode,
                'constraint_force': sim_state['forces']['constraint']['magnitude'] if sim_state else 0,
                'position_delta_m': (pos['latitude'] - current_lat) / 0.000009 if pos else 0
            })

            # Print every 10 seconds
            if i % 10 == 0 or i < 5:
                phase_name = "deployment in progress"
                for phase in deployment_phases:
                    if elapsed >= (len(samples) * 0.67 - 30) and elapsed < (len(samples) * 0.67):
                        phase_name = phase['name']
                        break

                print(f"[{elapsed:6.1f}s] Rode: {rode:6.1f}m | Speed: {spd:5.2f} m/s | "
                      f"Constraint: {samples[-1]['constraint_force']:7.1f} N | "
                      f"Pos delta: {samples[-1]['position_delta_m']:6.1f}m")

        time.sleep(1)

except KeyboardInterrupt:
    print("\n\nTest interrupted by user")

print("\n" + "="*70)
print("  CONSTRAINT FORCE ANALYSIS")
print("="*70 + "\n")

# Analyze constraint force at different phases
if samples:
    # Phase 1: Initial (0-5s) - should have 0 slack
    phase1 = [s for s in samples if s['time'] < 5]
    phase1_avg_constraint = sum(s['constraint_force'] for s in phase1) / len(phase1) if phase1 else 0
    print(f"Phase 1 (0-5s, initial drop):")
    print(f"  Avg constraint force: {phase1_avg_constraint:.1f} N")
    print(f"  Avg rode: {sum(s['rode'] for s in phase1) / len(phase1) if phase1 else 0:.1f}m")
    print(f"  Status: {'✓ Low constraint (slack present)' if phase1_avg_constraint < 50 else '✗ High constraint (no slack)'}\n")

    # Phase 2: Around 40% (30-35s) - anchor digging
    phase2 = [s for s in samples if 30 <= s['time'] <= 35]
    phase2_avg_constraint = sum(s['constraint_force'] for s in phase2) / len(phase2) if phase2 else 0
    phase2_avg_rode = sum(s['rode'] for s in phase2) / len(phase2) if phase2 else 0
    print(f"Phase 2 (30-35s, 40% scope - anchor digging):")
    print(f"  Avg constraint force: {phase2_avg_constraint:.1f} N")
    print(f"  Avg rode: {phase2_avg_rode:.1f}m (expected ~268m at 40%)")
    if phase2_avg_rode > 200:
        print(f"  Status: ✓ Approaching 40% scope\n")
    else:
        print(f"  Status: Still deploying, check back later\n")

    # Phase 3: Around 80% (75-80s) - fully dug
    phase3 = [s for s in samples if 75 <= s['time'] <= 80]
    phase3_avg_constraint = sum(s['constraint_force'] for s in phase3) / len(phase3) if phase3 else 0
    phase3_avg_rode = sum(s['rode'] for s in phase3) / len(phase3) if phase3 else 0
    print(f"Phase 3 (75-80s, 80% scope - anchor fully dug):")
    print(f"  Avg constraint force: {phase3_avg_constraint:.1f} N")
    print(f"  Avg rode: {phase3_avg_rode:.1f}m (expected ~536m at 80%)")
    if phase3_avg_rode > 400:
        print(f"  Status: ✓ Approaching 80% scope\n")
    else:
        print(f"  Status: Still deploying\n")

    # Phase 4: 100% (100+s)
    phase4 = [s for s in samples if s['time'] > 100]
    phase4_avg_constraint = sum(s['constraint_force'] for s in phase4) / len(phase4) if phase4 else 0
    phase4_avg_rode = sum(s['rode'] for s in phase4) / len(phase4) if phase4 else 0
    print(f"Phase 4 (100+s, 100% scope - fully deployed):")
    print(f"  Avg constraint force: {phase4_avg_constraint:.1f} N")
    print(f"  Avg rode: {phase4_avg_rode:.1f}m (expected ~670m at 100%)")
    if phase4_avg_rode > 600:
        print(f"  Status: ✓ Full deployment reached\n")
    else:
        print(f"  Status: Still deploying\n")

print("\nSummary:")
print(f"Total samples collected: {len(samples)}")
print(f"Total time: {samples[-1]['time']:.1f}s" if samples else "No data")
print(f"Final rode deployed: {samples[-1]['rode']:.1f}m" if samples else "No data")
print(f"Final constraint force: {samples[-1]['constraint_force']:.1f} N" if samples else "No data")

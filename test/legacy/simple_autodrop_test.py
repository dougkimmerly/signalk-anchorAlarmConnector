#!/usr/bin/env python3
"""
Simplified AutoDrop Test - 20kn Wind Only
Runs autoDrop, monitors until 5:1 scope reached, then resets and analyzes.
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime

auth_token = None

def get_auth_token():
    """Get authentication token from SignalK server"""
    global auth_token
    try:
        url = "http://localhost:80/signalk/v1/auth/login"
        credentials = {"username": "admin", "password": "signalk"}
        data = json.dumps(credentials).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')

        with urllib.request.urlopen(req, timeout=2) as response:
            result = json.loads(response.read())
            auth_token = result.get('token')
            if auth_token:
                print(f"✓ Authentication successful")
                return True
            else:
                print(f"✗ No token in response")
                return False
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return False

def get_signalk_data(path=""):
    """Get data from SignalK server"""
    try:
        url = f"http://localhost:80/signalk/v1/api/vessels/self{path}"
        with urllib.request.urlopen(url, timeout=3) as response:
            return json.loads(response.read())
    except:
        return None

def send_command(command):
    """Send command to anchor controller (autoDrop or autoRetrieve)"""
    global auth_token
    try:
        url = f"http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/command"
        data = json.dumps({"value": command}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {auth_token}')
        with urllib.request.urlopen(req, timeout=2) as response:
            return True
    except Exception as e:
        print(f"✗ Error sending {command} command: {e}")
        return False

def stop_controller():
    """Stop the chain controller"""
    global auth_token
    try:
        url = f"http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/command"
        data = json.dumps({"value": "stop"}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {auth_token}')
        with urllib.request.urlopen(req, timeout=2) as response:
            return True
    except:
        return False

def reset_anchor():
    """Reset anchor rode to 0m using standalone reset program"""
    import subprocess
    try:
        result = subprocess.run(['python3', 'reset_anchor.py'],
                              capture_output=True, text=True, timeout=20)
        print(result.stdout)
        return result.returncode == 0
    except Exception as e:
        print(f"✗ Reset error: {e}")
        return False

def get_current_metrics():
    """Get current position and deployment metrics"""
    data = get_signalk_data()
    if not data:
        return None

    nav = data.get('navigation', {})
    position = nav.get('position', {})
    anchor = nav.get('anchor', {})

    try:
        # Get boat heading - published as radians in a dict, convert to degrees
        heading_data = nav.get('headingTrue')
        if heading_data is not None:
            try:
                if isinstance(heading_data, dict):
                    heading_rad = float(heading_data.get('value', 0))
                else:
                    heading_rad = float(heading_data)
                heading = (heading_rad * 180 / 3.14159265359) % 360
            except:
                heading = None
        else:
            heading = None

        # Get speed - speedOverGround is published as dict with value key
        speed_data = nav.get('speedOverGround')
        if speed_data is not None:
            try:
                if isinstance(speed_data, dict):
                    boat_speed = float(speed_data.get('value', 0))
                else:
                    boat_speed = float(speed_data)
            except:
                boat_speed = 0
        else:
            boat_speed = 0

        # Get position - may be nested in 'value'
        pos_data = position.get('value')
        if isinstance(pos_data, dict):
            lat = pos_data.get('latitude')
            lon = pos_data.get('longitude')
        else:
            lat = position.get('latitude')
            lon = position.get('longitude')

        metrics = {
            'latitude': lat,
            'longitude': lon,
            'boat_speed': boat_speed,
            'boat_heading': heading,
            'distance': anchor.get('distanceFromBow', {}).get('value'),
            'rode_deployed': anchor.get('rodeDeployed', {}).get('value'),
            'chain_slack': anchor.get('chainSlack', {}).get('value', 0),
            'depth': nav.get('waterDepth', {}).get('value', 3.0),
        }
        return metrics
    except:
        return None

def check_scope_reached(samples, target_scope=5.0, expected_depth=3.0, bow_height=2.0):
    """Check if target scope has been reached"""
    if not samples:
        return False, 0, 0

    final = samples[-1]
    rode = final.get('rode_deployed', 0)
    depth = final.get('depth', expected_depth)

    if depth <= 0:
        depth = expected_depth

    scope = rode / (depth + bow_height) if (depth + bow_height) > 0 else 0
    return scope >= target_scope, rode, scope

def run_test():
    """Run simplified autoDrop test at 20kn"""

    print(f"\n{'='*70}")
    print(f"SIMPLIFIED AUTODROP TEST - 20kn WIND")
    print(f"{'='*70}\n")

    # Setup
    print("[1/5] Authenticating...")
    if not get_auth_token():
        print("✗ Failed to authenticate")
        return False

    print("[2/5] Stopping chain controller...")
    stop_controller()
    time.sleep(1)

    print("[3/5] Resetting anchor...")
    reset_anchor()
    time.sleep(2)

    # Verify reset
    metrics = get_current_metrics()
    if metrics:
        rode = metrics.get('rode_deployed', 0)
        print(f"   Current rode: {rode:.1f}m (target: 0m)")
        if rode > 0.5:
            print("✗ Reset verification failed")
            return False

    print("✓ System ready\n")

    # AutoDrop test
    print("[4/5] Starting autoDrop at 20kn wind...")
    if not send_command("autoDrop"):
        print("✗ Failed to send autoDrop command")
        return False

    print("✓ autoDrop started - monitoring until 5:1 scope reached\n")

    samples = []
    start_time = time.time()
    last_print = start_time
    scope_reached = False
    final_scope = 0
    final_rode = 0

    while time.time() - start_time < 240:  # Run for 240 seconds (4 minutes) to capture full deployment and boat movement
        metrics = get_current_metrics()
        elapsed = time.time() - start_time

        if metrics:
            metrics['time_sec'] = elapsed
            samples.append(metrics)

            # Check if scope reached
            is_complete, rode, scope = check_scope_reached(samples)

            if (elapsed - last_print) >= 3:
                heading_str = f"Heading={metrics['boat_heading']:6.1f}°" if metrics['boat_heading'] else "Heading=None"
                print(f"  {elapsed:6.0f}s: Rode={rode:6.1f}m  Dist={metrics['distance']:6.1f}m  Speed={metrics['boat_speed']:5.2f}m/s  {heading_str}  Scope={scope:5.2f}:1")
                last_print = elapsed

            if is_complete and not scope_reached:
                scope_reached = True
                final_scope = scope
                final_rode = rode
                print(f"\n✓ TARGET SCOPE REACHED: {final_scope:.2f}:1 (rode={final_rode:.1f}m)")

        # Adaptive sampling: faster during critical 5-10m rode range
        if metrics and 5 <= metrics.get('rode_deployed', 0) <= 10:
            time.sleep(0.05)  # 20Hz sampling during critical range
        else:
            time.sleep(0.1)   # 10Hz sampling rest of time

    if not scope_reached:
        print(f"\n⚠ Test ended without reaching target scope")
        if samples:
            final = samples[-1]
            rode = final.get('rode_deployed', 0)
            scope = rode / 5.0  # Approx with 3m depth + 2m bow
            print(f"  Final: Rode={rode:.1f}m, Approximate scope={scope:.2f}:1")

    # Save data
    print("\n[5/5] Saving test data and resetting...")
    filename = f"autodrop_20kn_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump({
            'test_type': 'autoDrop_simplified',
            'wind_speed_kn': 20,
            'samples': samples,
            'scope_reached': scope_reached,
            'final_scope': final_scope,
            'final_rode': final_rode
        }, f, indent=2)

    print(f"✓ Data saved to {filename}")

    # Reset
    stop_controller()
    time.sleep(1)
    reset_anchor()
    time.sleep(1)

    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    print(f"\nTo analyze results, run:")
    print(f"  python3 analyze_boat_movement.py {filename}\n")

    return True

if __name__ == '__main__':
    success = run_test()
    exit(0 if success else 1)

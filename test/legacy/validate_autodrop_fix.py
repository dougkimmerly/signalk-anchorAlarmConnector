#!/usr/bin/env python3
"""
Validate that autoDrop fix allows proper deployment to ~7m instead of stopping at 0.5m
Tests the fix for gradualMove mechanism during initial deployment phase
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
            return auth_token is not None
    except Exception as e:
        print(f"Error authenticating: {e}")
        return False

def reset_anchor():
    """Reset anchor system to initial state"""
    global auth_token
    try:
        # Stop any ongoing operation
        url = "http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/command"
        data = json.dumps({"value": "stop"}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {auth_token}')
        with urllib.request.urlopen(req, timeout=2):
            pass
        time.sleep(1)

        # Reset rodeDeployed to 0
        url = "http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/rodeDeployed"
        data = json.dumps({"value": 1}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {auth_token}')
        with urllib.request.urlopen(req, timeout=2):
            pass
        time.sleep(2)
        return True
    except Exception as e:
        print(f"Error resetting anchor: {e}")
        return False

def send_command(command):
    """Send command to anchor controller"""
    global auth_token
    try:
        url = "http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/command"
        data = json.dumps({"value": command}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {auth_token}')
        with urllib.request.urlopen(req, timeout=2):
            return True
    except Exception as e:
        print(f"Error sending command: {e}")
        return False

def get_anchor_status():
    """Get current anchor status"""
    try:
        url = "http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor"
        with urllib.request.urlopen(url, timeout=2) as response:
            return json.loads(response.read())
    except Exception as e:
        return None

def test_autodrop():
    """Test autoDrop deployment"""
    print("\n" + "="*70)
    print("TESTING AUTODROP FIX - Should deploy to ~7m, NOT stop at 0.5m")
    print("="*70)

    print("\nResetting system...")
    if not reset_anchor():
        print("✗ Failed to reset")
        return False
    time.sleep(1)

    print("✓ System reset")

    print("\nSending autoDrop command...")
    if not send_command("autoDrop"):
        print("✗ Failed to send autoDrop command")
        return False
    print("✓ autoDrop command sent")

    print("\nMonitoring deployment progress:")
    samples = []
    max_rode = 0
    stable_count = 0
    last_rode = 0

    for i in range(60):  # 60 second timeout
        status = get_anchor_status()
        if not status:
            print(f"  {i}s: Error getting status")
            time.sleep(1)
            continue

        current_rode = status.get('rodeDeployed', {}).get('value', 0)
        max_rode = max(max_rode, current_rode)

        # Check if deployment has stopped (stable for 3+ seconds)
        if abs(current_rode - last_rode) < 0.01:
            stable_count += 1
            if stable_count >= 3:
                print(f"  {i}s: Deployment complete at {current_rode:.2f}m")
                break
        else:
            stable_count = 0

        last_rode = current_rode
        samples.append({
            'time': i,
            'rode': current_rode
        })

        print(f"  {i}s: {current_rode:.2f}m", end="")
        if current_rode < 1.0:
            print(" ✓ (still in initial phase)")
        elif current_rode < 5.0:
            print(" ✓ (reaching seabed)")
        elif current_rode >= 7.0:
            print(" ✓ (FULL DEPLOYMENT - FIX WORKING!)")
        else:
            print()

        time.sleep(1)

    # Analyze results
    print("\n" + "-"*70)
    print("DEPLOYMENT ANALYSIS")
    print("-"*70)
    print(f"Maximum rode deployed: {max_rode:.2f}m")
    print(f"Final rode deployed: {last_rode:.2f}m")

    # Determine success
    success = False
    reason = ""

    if max_rode >= 6.5:  # Should reach ~7m (3m depth + 2m bow + 2m slack)
        success = True
        reason = f"✓ PASS - Deployed to {max_rode:.2f}m (target ~7m)"
    elif max_rode >= 5.0:
        success = True
        reason = f"⚠ PARTIAL - Deployed to {max_rode:.2f}m (expected ~7m)"
    elif max_rode >= 0.6:
        success = False
        reason = f"✗ FAIL - Stopped at {max_rode:.2f}m (old bug: stops at ~0.5m)"
    else:
        success = False
        reason = f"✗ FAIL - No deployment, only {max_rode:.2f}m"

    print(reason)
    print("="*70 + "\n")

    return success

def main():
    """Main test entry point"""
    print(f"\nStarted: {datetime.now().isoformat()}")

    # Authenticate
    print("\nAuthenticating...")
    if not get_auth_token():
        print("✗ Authentication failed")
        return False
    print("✓ Authenticated")

    # Run test
    success = test_autodrop()

    return success

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)

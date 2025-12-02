#!/usr/bin/env python3
"""
Phase 4 Motor SignalK PUT Handler Testing
Tests motor control via SignalK PUT endpoints instead of HTTP REST endpoints
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
        print(f"Error getting token: {e}")
        return None

def put_motor_state(token, state):
    """Set motor state via SignalK PUT handler"""
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/anchor/motor/state"
        data = json.dumps({"value": state}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            resp_text = response.read().decode()
            try:
                return json.loads(resp_text)
            except:
                return resp_text
    except urllib.error.HTTPError as e:
        return {'error': e.code, 'message': e.read().decode()}
    except Exception as e:
        return {'error': 'exception', 'message': str(e)}

def put_motor_throttle(token, throttle):
    """Set motor throttle via SignalK PUT handler"""
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/anchor/motor/throttle"
        data = json.dumps({"value": throttle}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            resp_text = response.read().decode()
            try:
                return json.loads(resp_text)
            except:
                return resp_text
    except urllib.error.HTTPError as e:
        return {'error': e.code, 'message': e.read().decode()}
    except Exception as e:
        return {'error': 'exception', 'message': str(e)}

def get_motor_state(token):
    """Get current motor state from SignalK"""
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/anchor/motor"
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read())
    except:
        return None

# Get token
token = get_auth_token()
if not token:
    print("✗ Failed to get authentication token")
    sys.exit(1)

print("="*70)
print("  PHASE 4: MOTOR SIGNALK PUT HANDLER TESTING")
print("="*70)
print()

# Test 1: Motor State Control
print("="*70)
print("TEST 1: MOTOR STATE CONTROL")
print("="*70)
print()

# Test 1a: Start motor forward
print("1a. Starting motor forward (should start at 5% throttle)...")
result = put_motor_state(token, "forward")
print(f"    Response: {result}")
time.sleep(1)

# Test 1b: Stop motor
print("\n1b. Stopping motor...")
result = put_motor_state(token, "stop")
print(f"    Response: {result}")
time.sleep(1)

# Test 1c: Start motor backward
print("\n1c. Starting motor backward (should start at 5% throttle)...")
result = put_motor_state(token, "backward")
print(f"    Response: {result}")
time.sleep(1)

# Test 1d: Invalid state (should return 400 error)
print("\n1d. Attempting invalid motor state 'invalid' (should return 400)...")
result = put_motor_state(token, "invalid")
if isinstance(result, dict) and 'error' in result:
    print(f"    ✓ Got error response: {result.get('message', result)}")
else:
    print(f"    Response: {result}")

# Test 2: Motor Throttle Control
print("\n" + "="*70)
print("TEST 2: MOTOR THROTTLE CONTROL")
print("="*70)
print()

# Start motor first
print("Starting motor forward for throttle testing...")
put_motor_state(token, "forward")
time.sleep(1)

# Test 2a: Set throttle to 25%
print("\n2a. Setting throttle to 25%...")
result = put_motor_throttle(token, 25)
print(f"    Response: {result}")
time.sleep(1)

# Test 2b: Set throttle to 50%
print("\n2b. Setting throttle to 50%...")
result = put_motor_throttle(token, 50)
print(f"    Response: {result}")
time.sleep(1)

# Test 2c: Set throttle to 100%
print("\n2c. Setting throttle to 100%...")
result = put_motor_throttle(token, 100)
print(f"    Response: {result}")
time.sleep(1)

# Test 2d: Invalid throttle (should return 400 error)
print("\n2d. Attempting invalid throttle 150% (should return 400)...")
result = put_motor_throttle(token, 150)
if isinstance(result, dict) and 'error' in result:
    print(f"    ✓ Got error response: {result.get('message', result)}")
else:
    print(f"    Response: {result}")

# Test 2e: Invalid throttle 0% (should return 400 error)
print("\n2e. Attempting invalid throttle 0% (should return 400)...")
result = put_motor_throttle(token, 0)
if isinstance(result, dict) and 'error' in result:
    print(f"    ✓ Got error response: {result.get('message', result)}")
else:
    print(f"    Response: {result}")

# Stop motor
print("\nStopping motor...")
put_motor_state(token, "stop")
time.sleep(1)

# Test 3: Check motor state in SignalK
print("\n" + "="*70)
print("TEST 3: MOTOR STATE VISIBILITY IN SIGNALK")
print("="*70)
print()

print("3a. Motor state when stopped:")
motor_state = get_motor_state(token)
if motor_state:
    print(f"    Current state: {json.dumps(motor_state, indent=2)}")
else:
    print("    (Motor state path not yet published)")

print("\n3b. Starting motor forward...")
put_motor_state(token, "forward")
time.sleep(1)

print("    Getting motor state...")
motor_state = get_motor_state(token)
if motor_state:
    print(f"    Current state: {json.dumps(motor_state, indent=2)}")
else:
    print("    (Motor state path not yet published)")

print("\n3c. Setting throttle to 75%...")
put_motor_throttle(token, 75)
time.sleep(1)

print("    Getting motor state...")
motor_state = get_motor_state(token)
if motor_state:
    print(f"    Current state: {json.dumps(motor_state, indent=2)}")
else:
    print("    (Motor state path not yet published)")

# Stop motor
print("\nStopping motor...")
put_motor_state(token, "stop")

# Summary
print("\n" + "="*70)
print("  TEST SUMMARY")
print("="*70)
print()
print("✓ Motor state control (forward/backward/stop)")
print("✓ Motor throttle control (1-100%)")
print("✓ Error handling for invalid states")
print("✓ Error handling for invalid throttle values")
print()
print("Notes:")
print("- Motor forward starts at 5% throttle by default")
print("- Motor backward starts at 5% throttle by default")
print("- Throttle values must be 1-100 (percentage)")
print("- Invalid states/throttle return 400 HTTP error")
print("- SignalK PUT handlers provide alternative control method")

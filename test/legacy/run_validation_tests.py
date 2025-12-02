#!/usr/bin/env python3
"""
Validation test runner with proper shutdown and stall detection.
Runs multiple tests sequentially with complete resets between them.
"""

import json
import time
import subprocess
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
        print(f"✗ Authentication failed: {e}")
        return False

def stop_controller():
    """Stop the chain controller immediately"""
    global auth_token
    try:
        url = "http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/command"
        data = json.dumps({"value": "stop"}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {auth_token}')
        with urllib.request.urlopen(req, timeout=2) as response:
            return True
    except:
        return False

def reset_anchor():
    """Reset anchor rode to 0m"""
    try:
        result = subprocess.run(['python3', 'reset_anchor.py'],
                              capture_output=True, text=True, timeout=20)
        return result.returncode == 0
    except Exception as e:
        print(f"✗ Reset error: {e}")
        return False

def get_boat_position():
    """Get current boat position and metrics"""
    try:
        url = "http://localhost:80/signalk/v1/api/vessels/self"
        with urllib.request.urlopen(url, timeout=2) as response:
            data = json.loads(response.read())
            nav = data.get('navigation', {})
            pos = nav.get('position', {})
            if pos and 'value' in pos:
                val = pos['value']
                return {
                    'latitude': val.get('latitude'),
                    'longitude': val.get('longitude'),
                    'rode': nav.get('anchor', {}).get('rodeDeployed', {}).get('value', 0),
                    'speed': nav.get('speedOverGround', {}).get('value', 0)
                }
    except:
        pass
    return None

def run_single_test(test_num):
    """Run a single test with stall detection"""
    print(f"\n{'='*80}")
    print(f"TEST {test_num}: Starting test sequence")
    print(f"{'='*80}")

    # Stop any running operations
    print(f"[{test_num}] Stopping chain controller...")
    stop_controller()
    time.sleep(1)

    # Reset anchor
    print(f"[{test_num}] Resetting anchor...")
    if not reset_anchor():
        print(f"[{test_num}] ✗ Reset failed")
        return False
    time.sleep(2)

    # Start test
    print(f"[{test_num}] Starting autoDrop test...")
    test_start = time.time()
    last_position = get_boat_position()
    if not last_position:
        print(f"[{test_num}] ✗ Could not get initial position")
        return False

    last_movement_time = time.time()
    stall_threshold = 80  # seconds
    test_timeout = 240  # max test duration

    # Start the test in background
    try:
        proc = subprocess.Popen(
            ['python3', 'simple_autodrop_test.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except Exception as e:
        print(f"[{test_num}] ✗ Failed to start test: {e}")
        return False

    # Monitor test for stall or completion
    while True:
        elapsed = time.time() - test_start

        # Check if test process is still running
        if proc.poll() is not None:
            # Process finished
            stdout, stderr = proc.communicate()
            print(f"[{test_num}] ✓ Test completed in {elapsed:.1f}s")
            print(stdout)
            return True

        # Check for timeout
        if elapsed > test_timeout:
            print(f"[{test_num}] ✗ Test timeout ({test_timeout}s)")
            proc.terminate()
            time.sleep(2)
            proc.kill()
            return False

        # Check for stall (no movement for 80 seconds)
        current_pos = get_boat_position()
        if current_pos:
            moved = (abs(current_pos['latitude'] - last_position['latitude']) > 0.00001 or
                    abs(current_pos['longitude'] - last_position['longitude']) > 0.00001)

            if moved:
                last_movement_time = time.time()
                last_position = current_pos
                print(f"[{test_num}] ✓ Movement detected: lat={current_pos['latitude']:.8f}, "
                      f"lon={current_pos['longitude']:.8f}, rode={current_pos['rode']:.1f}m")
            else:
                stall_time = time.time() - last_movement_time
                if stall_time > stall_threshold:
                    print(f"[{test_num}] ✗ STALL DETECTED: No movement for {stall_time:.1f}s")
                    print(f"[{test_num}] Terminating test")
                    proc.terminate()
                    time.sleep(2)
                    proc.kill()
                    return False

        time.sleep(5)  # Check every 5 seconds

def cleanup_after_test(test_num):
    """Ensure complete cleanup after test"""
    print(f"[{test_num}] Cleanup: Stopping controller...")
    stop_controller()
    time.sleep(2)
    print(f"[{test_num}] ✓ Cleanup complete - ready for next test")

def main():
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "VALIDATION TEST SUITE - SEQUENTIAL EXECUTION" + " "*15 + "║")
    print("╚" + "="*78 + "╝")

    if not get_auth_token():
        print("✗ Failed to authenticate with SignalK server")
        return False

    results = []
    num_tests = 5

    for test_num in range(1, num_tests + 1):
        # Run test
        success = run_single_test(test_num)
        results.append({
            'test': test_num,
            'success': success
        })

        # Cleanup before next test
        if test_num < num_tests:
            cleanup_after_test(test_num)
            print(f"\nWaiting 5 seconds before Test {test_num + 1}...")
            time.sleep(5)

    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    for r in results:
        status = "✓ PASS" if r['success'] else "✗ FAIL"
        print(f"Test {r['test']}: {status}")

    passed = sum(1 for r in results if r['success'])
    print(f"\nTotal: {passed}/{num_tests} tests passed")

    return passed == num_tests

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
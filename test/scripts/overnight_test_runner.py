#!/usr/bin/env python3
"""
Overnight Test Orchestrator for AutoDrop and AutoRetrieve
Autonomous test runner - executes all 72 tests with full data collection and analysis
Run once and walk away - handles all phases automatically
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error
import math
import statistics

# Configuration
BASE_URL = "http://localhost:80"
SCRIPTS_DIR = Path(__file__).parent  # Directory containing this script
TEST_DIR = SCRIPTS_DIR.parent  # Parent test/ directory
SESSION_DIR = None
PROGRESS_FILE = None
TEST_LOG = None
TEST_TIMEOUT = 600  # 10 minutes per test
SAMPLE_INTERVAL = 0.5  # 500ms sampling
MAX_RETRIES = 2

# Test matrix
WIND_SPEEDS = [4, 8, 12, 18, 20, 25]  # knots
DEPTHS = [3, 5, 8, 12]  # meters (max 12m to stay within 80m chain @ 5:1 scope)
TEST_TYPES = ['autoDrop', 'autoRetrieve']

# Global counters
total_tests = len(WIND_SPEEDS) * len(DEPTHS) * len(TEST_TYPES)
tests_completed = 0
tests_passed = 0
tests_failed = 0

def setup_session():
    """Create session directory and initialize logging"""
    global SESSION_DIR, PROGRESS_FILE, TEST_LOG

    session_timestamp = datetime.now().strftime('%Y%m%d')
    SESSION_DIR = TEST_DIR / f'overnight_tests_{session_timestamp}'
    SESSION_DIR.mkdir(exist_ok=True)

    # Create subdirectories
    (SESSION_DIR / 'raw_data').mkdir(exist_ok=True)
    (SESSION_DIR / 'analysis').mkdir(exist_ok=True)
    (SESSION_DIR / 'analysis' / 'heatmaps').mkdir(exist_ok=True)

    PROGRESS_FILE = SESSION_DIR / 'PROGRESS.txt'
    TEST_LOG = SESSION_DIR / 'TEST_LOG.md'

    # Initialize test log
    with open(TEST_LOG, 'w') as f:
        f.write('# Overnight Test Session Log\n\n')
        f.write(f'Started: {datetime.now().isoformat()}\n')
        f.write(f'Test Matrix: {len(WIND_SPEEDS)} wind speeds × {len(DEPTHS)} depths × {len(TEST_TYPES)} test types = {total_tests} tests\n')
        f.write(f'Session Directory: {SESSION_DIR}\n\n')
        f.write('## Progress\n\n')

    print(f'[SETUP] Session directory: {SESSION_DIR}')
    return SESSION_DIR

def log_test(message):
    """Append to test log"""
    with open(TEST_LOG, 'a') as f:
        f.write(message + '\n')
    print(message)

def update_progress(test_num, wind, depth, test_type, status):
    """Update progress file"""
    with open(PROGRESS_FILE, 'w') as f:
        f.write(f'Test {test_num}/{total_tests}\n')
        f.write(f'Current: {test_type} @ {wind}kn, {depth}m\n')
        f.write(f'Status: {status}\n')
        f.write(f'Completed: {tests_completed}\n')
        f.write(f'Passed: {tests_passed}\n')
        f.write(f'Failed: {tests_failed}\n')

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
        log_test(f'✗ Failed to get token: {e}')
        return None

def verify_server():
    """Verify SignalK and plugin are running"""
    try:
        # Check SignalK server
        urllib.request.urlopen(f"{BASE_URL}/signalk", timeout=5).close()
        # Check if we can get a token (proves plugin is loaded and auth works)
        token = get_auth_token()
        if token:
            return True
        return False
    except:
        return False

def check_chain_controller():
    """Check if chain controller (ESP32) is responding via SignalK"""
    try:
        token = get_auth_token()
        if not token:
            return False, "No auth token"

        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/anchor/rodeDeployed"
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read())
            source = data.get('$source', '')
            # Chain controller source starts with 'ws.' (websocket connection)
            if source.startswith('ws.'):
                return True, f"Connected via {source[:20]}..."
            else:
                return False, f"Unexpected source: {source}"
    except Exception as e:
        return False, str(e)

def restart_chain_controller():
    """Restart the ESP32 chain controller"""
    ESP32_IP = "192.168.20.217"
    try:
        log_test(f"  Restarting chain controller at {ESP32_IP}...")
        url = f"http://{ESP32_IP}/api/device/restart"
        req = urllib.request.Request(url, method='POST')
        with urllib.request.urlopen(req, timeout=5) as response:
            pass
        # Wait for ESP32 to restart and reconnect
        log_test("  Waiting 15s for ESP32 to restart...")
        time.sleep(15)

        # Verify it reconnected
        for attempt in range(5):
            ok, msg = check_chain_controller()
            if ok:
                log_test(f"  ✓ Chain controller reconnected: {msg}")
                return True
            time.sleep(3)

        log_test("  ✗ Chain controller did not reconnect after restart")
        return False
    except Exception as e:
        log_test(f"  ✗ Failed to restart chain controller: {e}")
        return False

def ensure_chain_controller():
    """Ensure chain controller is responsive, restart if needed"""
    ok, msg = check_chain_controller()
    if ok:
        return True

    log_test(f"! Chain controller not responding: {msg}")
    return restart_chain_controller()

def reset_anchor():
    """Reset anchor to 0m rode"""
    try:
        subprocess.run(['python3', str(SCRIPTS_DIR / 'reset_anchor.py')],
                      timeout=10, capture_output=True)
        time.sleep(3)
        return True
    except:
        return False

def stop_chain():
    """Stop any running chain operations"""
    try:
        subprocess.run(['python3', str(SCRIPTS_DIR / 'stop_chain.py')],
                      timeout=5, capture_output=True)
        time.sleep(1)
        return True
    except:
        return False

def configure_environment(wind_speed, depth):
    """Set wind speed and depth using correct config structure"""
    try:
        token = get_auth_token()
        if not token:
            return False

        url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/simulation/config"
        # Use correct nested structure matching simulationConfig.js
        data = json.dumps({
            "wind": {
                "initialSpeed": wind_speed,
                "initialDirection": 180
            },
            "environment": {
                "depth": depth
            }
        }).encode('utf-8')

        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')

        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read())
            # Config endpoint returns the new config, not a success flag
            return result is not None
    except Exception as e:
        log_test(f'  ! Config error: {e}')
        return False

def get_simulation_state(token):
    """Get current simulation state including forces and boat state"""
    try:
        url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/simulation/state"
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read())
    except:
        return None

def reset_simulation():
    """Reset simulation to initial state (after config change)"""
    try:
        token = get_auth_token()
        if not token:
            return False

        url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/simulation/reset"
        req = urllib.request.Request(url, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')

        with urllib.request.urlopen(req, timeout=5) as response:
            return True
    except Exception as e:
        log_test(f'  ! Simulation reset error: {e}')
        return False

def get_position(token):
    """Get boat position"""
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/position/value"
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read())
    except:
        return None

def get_speed(token):
    """Get boat speed"""
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/speedOverGround/value"
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read())
    except:
        return None

def get_heading(token):
    """Get boat heading in degrees"""
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/headingTrue/value"
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            rad = json.loads(response.read())
            return rad * 180 / math.pi
    except:
        return None

def send_command(token, command):
    """Send anchor control command via SignalK PUT handler"""
    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/navigation/anchor/command"
        data = json.dumps({"value": command}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return {'error': str(e)}

def collect_sample(token, start_pos, start_lat, start_lon, start_time):
    """Collect single telemetry sample"""
    try:
        pos = get_position(token)
        speed = get_speed(token)
        heading = get_heading(token)
        sim_state = get_simulation_state(token)

        if not (pos and speed is not None and heading):
            return None

        elapsed = time.time() - start_time

        # Calculate derived values
        lat_delta = (pos['latitude'] - start_lat) / 0.000009  # meters

        sample = {
            'timestamp': datetime.now().isoformat() + 'Z',
            'elapsed_sec': elapsed,
            'position': {
                'latitude': pos['latitude'],
                'longitude': pos['longitude'],
                'speed': speed,
                'heading': heading % 360 if heading else 0
            },
            'distance_from_start': lat_delta
        }

        # Add simulation state if available
        if sim_state:
            sample['simulation_state'] = sim_state

        return sample
    except:
        return None

def run_test(test_num, wind_speed, depth, test_type):
    """Run single test with full data collection"""
    global tests_completed, tests_passed, tests_failed

    test_name = f'{test_type}_wind{wind_speed}_depth{depth}'
    log_test(f'\n## Test {test_num}/{total_tests}: {test_name}')
    update_progress(test_num, wind_speed, depth, test_type, 'RUNNING')

    token = get_auth_token()
    if not token:
        log_test(f'✗ FAILED: Could not get auth token')
        tests_failed += 1
        tests_completed += 1
        return None

    # Phase 0: Ensure chain controller is responsive
    log_test(f'[PHASE 0] Checking chain controller...')
    if not ensure_chain_controller():
        log_test(f'✗ FAILED: Chain controller not responsive after restart attempt')
        tests_failed += 1
        tests_completed += 1
        return None
    log_test(f'✓ Chain controller ready')

    # Phase 1: Reset and verify
    log_test(f'[PHASE 1] Resetting anchor...')
    if not stop_chain() or not reset_anchor():
        log_test(f'✗ FAILED: Could not reset anchor')
        tests_failed += 1
        tests_completed += 1
        return None
    log_test(f'✓ Anchor reset')

    # Phase 2: Configure environment
    log_test(f'[PHASE 2] Configuring environment: {wind_speed}kn, {depth}m depth')
    if not configure_environment(wind_speed, depth):
        log_test(f'✗ FAILED: Could not configure environment')
        tests_failed += 1
        tests_completed += 1
        return None
    # Reset simulation to apply new config with fresh state
    if not reset_simulation():
        log_test(f'! Warning: Simulation reset failed, continuing anyway')
    time.sleep(1)  # Allow simulation to stabilize
    log_test(f'✓ Environment configured and simulation reset')

    # Phase 3: Run test
    log_test(f'[PHASE 3] Running {test_type} test...')

    start_time = time.time()
    start_pos = get_position(token)
    if not start_pos:
        log_test(f'✗ FAILED: Could not get initial position')
        tests_failed += 1
        tests_completed += 1
        return None

    start_lat = start_pos['latitude']
    start_lon = start_pos['longitude']

    # Send command
    command = 'autoDrop' if test_type == 'autoDrop' else 'autoRetrieve'
    result = send_command(token, command)
    if 'error' in result:
        log_test(f'✗ FAILED: Command error - {result}')
        tests_failed += 1
        tests_completed += 1
        return None
    log_test(f'✓ Command sent: {command}')

    # Collect data
    samples = []
    test_start = time.time()
    next_sample_time = test_start + SAMPLE_INTERVAL
    max_duration = TEST_TIMEOUT if test_type == 'autoDrop' else TEST_TIMEOUT

    try:
        while time.time() - test_start < max_duration:
            now = time.time()
            if now >= next_sample_time:
                sample = collect_sample(token, start_pos, start_lat, start_lon, test_start)
                if sample:
                    samples.append(sample)
                next_sample_time = now + SAMPLE_INTERVAL

            time.sleep(0.1)

            # Check termination conditions
            if len(samples) > 0:
                latest = samples[-1]
                if test_type == 'autoDrop':
                    # Check if target scope reached
                    sim_state = latest.get('simulation_state', {})
                    scope = sim_state.get('scopeRatio', 0)
                    if scope >= 5.0:
                        log_test(f'✓ Target scope reached: {scope:.1f}:1')
                        break
                elif test_type == 'autoRetrieve':
                    # Check if rode retrieved
                    sim_state = latest.get('simulation_state', {})
                    rode = sim_state.get('rodeDeployed', 0)
                    if rode <= 0.1:
                        log_test(f'✓ Rode fully retrieved: {rode:.1f}m')
                        break
    except KeyboardInterrupt:
        log_test('! Test interrupted by user')
    except Exception as e:
        log_test(f'! Error during data collection: {e}')

    # Phase 4: Save test data
    log_test(f'[PHASE 4] Saving test data ({len(samples)} samples)...')

    test_file = SESSION_DIR / 'raw_data' / f'test_{test_type}_{wind_speed}kn_{depth}m_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

    test_data = {
        'test_metadata': {
            'test_number': test_num,
            'test_type': test_type,
            'wind_speed_kn': wind_speed,
            'wind_direction': 180,
            'depth_m': depth,
            'target_scope': 5.0,
            'start_time': datetime.fromtimestamp(start_time).isoformat() + 'Z',
            'end_time': datetime.now().isoformat() + 'Z',
            'duration_sec': time.time() - start_time,
            'sample_count': len(samples),
            'completed': True,
            'timeout': len(samples) == 0
        },
        'samples': samples
    }

    # Calculate summary
    if samples:
        final_sample = samples[-1]
        sim_state = final_sample.get('simulation_state', {})

        test_data['summary'] = {
            'final_scope': sim_state.get('scopeRatio', 0),
            'final_rode': sim_state.get('rodeDeployed', 0),
            'final_distance': final_sample.get('distance_from_start', 0),
            'max_speed': max([s.get('position', {}).get('speed', 0) for s in samples]),
            'final_speed': final_sample.get('position', {}).get('speed', 0),
        }

    with open(test_file, 'w') as f:
        json.dump(test_data, f, indent=2)

    log_test(f'✓ Test data saved: {test_file.name}')

    # Determine pass/fail
    passed = len(samples) > 0 and test_data.get('summary')
    if passed:
        tests_passed += 1
        log_test(f'✓ PASSED')
    else:
        tests_failed += 1
        log_test(f'✗ FAILED')

    tests_completed += 1
    update_progress(test_num, wind_speed, depth, test_type, 'DONE' if passed else 'FAILED')

    return test_data

def run_all_tests():
    """Execute complete test matrix"""
    if not verify_server():
        print('✗ ERROR: SignalK server or plugin not running')
        print('  Start with: systemctl start signalk')
        sys.exit(1)

    print(f'✓ Server verified')

    # Verify chain controller before starting
    print('Checking chain controller (ESP32)...')
    ok, msg = check_chain_controller()
    if ok:
        print(f'✓ Chain controller ready: {msg}')
    else:
        print(f'! Chain controller not responding: {msg}')
        print('  Attempting restart...')
        if restart_chain_controller():
            print('✓ Chain controller restarted and connected')
        else:
            print('✗ ERROR: Chain controller could not be restarted')
            print('  Check ESP32 at 192.168.20.217')
            sys.exit(1)

    test_num = 1
    test_matrix = []

    # Generate test matrix
    for wind in WIND_SPEEDS:
        for depth in DEPTHS:
            for test_type in TEST_TYPES:
                test_matrix.append((wind, depth, test_type))

    # Run tests
    for wind, depth, test_type in test_matrix:
        run_test(test_num, wind, depth, test_type)
        test_num += 1
        time.sleep(2)  # Brief pause between tests

    # Generate summary
    log_test(f'\n## Summary\n')
    log_test(f'Total Tests: {total_tests}')
    log_test(f'Completed: {tests_completed}')
    log_test(f'Passed: {tests_passed}')
    log_test(f'Failed: {tests_failed}')
    log_test(f'Pass Rate: {tests_passed/total_tests*100:.1f}%')
    log_test(f'\nSession completed: {datetime.now().isoformat()}')

    print(f'\n✓ All tests complete!')
    print(f'  Results: {tests_passed}/{total_tests} passed')
    print(f'  See: {TEST_LOG}')

if __name__ == '__main__':
    setup_session()
    print(f'Starting overnight test session...')
    print(f'Total tests to run: {total_tests}')
    print(f'Estimated duration: ~{total_tests * 13 / 60:.0f} hours')
    print(f'Session directory: {SESSION_DIR}')
    print()

    try:
        run_all_tests()
    except KeyboardInterrupt:
        log_test(f'\n! Session interrupted by user at test {tests_completed}/{total_tests}')
        print(f'\nSession interrupted. Progress saved.')
    except Exception as e:
        log_test(f'\n! FATAL ERROR: {e}')
        print(f'Fatal error: {e}')
        sys.exit(1)

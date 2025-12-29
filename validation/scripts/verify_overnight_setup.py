#!/usr/bin/env python3
"""
Verify Overnight Test Setup
Checks all prerequisites before starting the test session
"""

import sys
import subprocess
import urllib.request
import urllib.error
import json
from pathlib import Path

# Directory paths
SCRIPTS_DIR = Path(__file__).parent  # Directory containing this script
TEST_DIR = SCRIPTS_DIR.parent  # Parent test/ directory

def check_signalk_server():
    """Check if SignalK server is running"""
    print('Checking SignalK server...')
    try:
        urllib.request.urlopen('http://localhost:80/signalk', timeout=5).close()
        print('  ✓ SignalK server responding')
        return True
    except:
        print('  ✗ SignalK server not responding')
        print('    Start with: systemctl start signalk')
        return False

def check_plugin():
    """Check if anchor alarm connector plugin is loaded"""
    print('Checking plugin...')
    try:
        urllib.request.urlopen('http://localhost:80/plugins/signalk-anchoralarmconnector', timeout=5).close()
        print('  ✓ Anchor alarm connector plugin loaded')
        return True
    except:
        print('  ✗ Plugin not loaded')
        print('    Check: curl http://localhost:80/plugins')
        return False

def check_authentication():
    """Check if authentication works"""
    print('Checking authentication...')
    try:
        url = 'http://localhost:80/signalk/v1/auth/login'
        data = json.dumps({"username": "admin", "password": "signalk"}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read())
            if result.get('token'):
                print('  ✓ Authentication working')
                return True
    except:
        pass

    print('  ✗ Authentication failed')
    return False

def check_simulation_state():
    """Check if simulation state is accessible"""
    print('Checking simulation state endpoint...')
    try:
        # First get token
        url = 'http://localhost:80/signalk/v1/auth/login'
        data = json.dumps({"username": "admin", "password": "signalk"}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=5) as response:
            token = json.loads(response.read()).get('token')

        # Then check simulation state
        url = 'http://localhost:80/plugins/signalk-anchoralarmconnector/simulation/state'
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            state = json.loads(response.read())
            if state:
                print('  ✓ Simulation state endpoint working')
                print(f'    Current state: {state}')
                return True
    except Exception as e:
        print(f'  ✗ Simulation state error: {e}')
        return False

def check_helper_scripts():
    """Check if helper scripts exist"""
    print('Checking helper scripts...')
    scripts = [
        SCRIPTS_DIR / 'reset_anchor.py',
        SCRIPTS_DIR / 'stop_chain.py',
        TEST_DIR / 'analysis' / 'test_analyzer.py'
    ]

    all_exist = True
    for script in scripts:
        if script.exists():
            print(f'  ✓ {script.name}')
        else:
            print(f'  ✗ {script.name} - NOT FOUND')
            all_exist = False

    return all_exist

def check_test_runner():
    """Check if test runner exists"""
    print('Checking test runner script...')
    runner = SCRIPTS_DIR / 'overnight_test_runner.py'
    if runner.exists():
        print(f'  ✓ overnight_test_runner.py found')
        return True
    else:
        print(f'  ✗ overnight_test_runner.py NOT FOUND')
        return False

def check_disk_space():
    """Check available disk space"""
    print('Checking disk space...')
    try:
        result = subprocess.run(['df', '/home/doug'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            parts = lines[1].split()
            available_gb = int(parts[3]) / 1024 / 1024
            print(f'  ✓ {available_gb:.1f} GB available')
            if available_gb > 5:
                print('    (Sufficient for test data)')
                return True
            else:
                print('    WARNING: May not be enough for full test session')
                return False
    except:
        print('  ! Could not determine disk space')
        return True

def main():
    """Run all checks"""
    print('=' * 70)
    print('Overnight Test Setup Verification')
    print('=' * 70)
    print()

    checks = [
        ('SignalK Server', check_signalk_server),
        ('Plugin', check_plugin),
        ('Authentication', check_authentication),
        ('Simulation State', check_simulation_state),
        ('Helper Scripts', check_helper_scripts),
        ('Test Runner', check_test_runner),
        ('Disk Space', check_disk_space),
    ]

    results = {}
    for name, check_fn in checks:
        try:
            results[name] = check_fn()
        except Exception as e:
            print(f'  ! Exception: {e}')
            results[name] = False
        print()

    # Summary
    print('=' * 70)
    print('Verification Summary')
    print('=' * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = '✓' if result else '✗'
        print(f'{status} {name}')

    print()
    print(f'Result: {passed}/{total} checks passed')
    print()

    if passed == total:
        print('✓ Ready to start overnight test session!')
        print()
        print('Run tests with:')
        print(f'  cd {SCRIPTS_DIR}')
        print('  python3 overnight_test_runner.py')
        print()
        print('Monitor progress with:')
        print(f'  tail -f {TEST_DIR.parent}/data/overnight_tests_YYYYMMDD_HHMMSS/TEST_LOG.md')
        return 0
    else:
        print('✗ Fix issues above before starting tests')
        return 1

if __name__ == '__main__':
    sys.exit(main())

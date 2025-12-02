#!/usr/bin/env python3
"""
Simple anchor reset utility
Sends reset command via SignalK: PUT to navigation.anchor.rodeDeployed with value=1
"""

import json
import time
import urllib.request
import urllib.error
import sys
from pathlib import Path

# Add test/utils to path so we can import common
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from common import get_auth_token

def get_rode_deployed(token):
    """Get current rode deployed value"""
    try:
        url = "http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/rodeDeployed"
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {token}')

        with urllib.request.urlopen(req, timeout=2) as response:
            result = json.loads(response.read())
            return result.get('value', None)
    except Exception as e:
        return None

def reset_rode(token):
    """Send reset command (PUT rodeDeployed = 1)"""
    try:
        url = "http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/rodeDeployed"
        data = json.dumps({"value": 1}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')

        with urllib.request.urlopen(req, timeout=2) as response:
            return True
    except Exception as e:
        print(f"Error sending reset: {e}")
        return False

def main():
    print("Resetting anchor rode to 0m...")

    # Get token
    token = get_auth_token()
    if not token:
        print("✗ Failed to authenticate")
        return False

    # Check current rode
    current = get_rode_deployed(token)
    if current is not None:
        print(f"Current rode: {current:.1f}m")

    # Send reset
    if not reset_rode(token):
        print("✗ Reset command failed")
        return False

    print("✓ Reset command sent")

    # Verify reset (wait up to 10 seconds)
    for attempt in range(10):
        time.sleep(1)
        rode = get_rode_deployed(token)
        if rode is not None:
            print(f"   Rode: {rode:.1f}m")
            if rode < 0.5:
                print("✓ Reset verified - rode is 0m")
                return True

    print("✗ Reset verification failed - rode did not reach 0m")
    return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

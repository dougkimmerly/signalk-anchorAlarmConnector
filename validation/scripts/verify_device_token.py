#!/usr/bin/env python3
"""
Verify that device token is available for test scripts.

This helper checks if the plugin has been approved in SignalK and a valid
device token exists. Run this before running test suites to ensure authentication
will work.
"""

import sys
from pathlib import Path

# Add test/utils to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from common import get_device_token

def main():
    print("Checking for device token...")
    print()

    token = get_device_token()
    if token:
        print("✓ Device token is available")
        print(f"✓ Token length: {len(token)} characters")
        print()
        print("All test scripts can now use this device token for authentication.")
        return True
    else:
        print("✗ No device token found")
        print()
        print("To fix this:")
        print("1. Ensure the SignalK plugin is running")
        print("2. Go to SignalK admin UI: http://localhost:80/admin/")
        print("3. Navigate to: Security → Access Requests")
        print("4. Look for 'signalk-anchor-alarm-connector' request")
        print("5. Click 'APPROVE' button")
        print()
        print("The device token will be saved to:")
        token_path = Path(__file__).parent.parent.parent / 'plugin' / 'data' / 'token.json'
        print(f"  {token_path}")
        print()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

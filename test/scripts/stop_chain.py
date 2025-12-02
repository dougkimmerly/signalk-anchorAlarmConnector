#!/usr/bin/env python3
"""
Stop the chain controller immediately
Sends stop command via SignalK: PUT to navigation.anchor.command with value='stop'
"""

import json
import time
import urllib.request
import urllib.error
import sys

def get_auth_token():
    """Get authentication token from SignalK server"""
    try:
        url = "http://localhost:80/signalk/v1/auth/login"
        credentials = {"username": "admin", "password": "signalk"}
        data = json.dumps(credentials).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')

        with urllib.request.urlopen(req, timeout=2) as response:
            result = json.loads(response.read())
            token = result.get('token')
            if token:
                return token
            else:
                print("Error: No token in response")
                return None
    except Exception as e:
        print(f"Error authenticating: {e}")
        return None

def stop_chain(token):
    """Send stop command to chain controller"""
    try:
        url = "http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/command"
        data = json.dumps({"value": "stop"}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')

        with urllib.request.urlopen(req, timeout=2) as response:
            return True
    except Exception as e:
        print(f"Error sending stop: {e}")
        return False

def main():
    print("Stopping chain controller...")

    # Get token
    token = get_auth_token()
    if not token:
        print("✗ Failed to authenticate")
        return False

    # Send stop command
    if not stop_chain(token):
        print("✗ Stop command failed")
        return False

    print("✓ Chain controller stopped")
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
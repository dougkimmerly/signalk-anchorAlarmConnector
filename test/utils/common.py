#!/usr/bin/env python3
"""
Common utilities for anchor alarm connector tests.

This module provides shared functions used across multiple test scripts,
eliminating code duplication and ensuring consistent behavior.
"""

import json
import urllib.request
import urllib.error
import time
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:80"
ESP32_IP = "192.168.20.217"

# Coordinate conversion constants (approximate at lat 43.6°)
METERS_TO_LAT = 0.000009
METERS_TO_LON = 0.0000125
BOW_HEIGHT = 2.0  # meters


# =============================================================================
# Authentication
# =============================================================================

def get_auth_token():
    """Get authentication token from SignalK server.

    Returns:
        str: JWT token if successful, None otherwise
    """
    try:
        url = f"{BASE_URL}/signalk/v1/auth/login"
        data = json.dumps({"username": "admin", "password": "signalk"}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read()).get('token')
    except Exception as e:
        print(f"Auth error: {e}")
        return None


# =============================================================================
# SignalK API - Reading
# =============================================================================

def get_signalk_value(path, token=None):
    """Get a value from SignalK API.

    Args:
        path: SignalK path (e.g., 'navigation.position')
        token: Optional auth token (will fetch if not provided)

    Returns:
        dict or value if successful, None otherwise
    """
    if token is None:
        token = get_auth_token()
    if not token:
        return None

    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/{path}"
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read())
    except Exception as e:
        return None


def get_position(token=None):
    """Get current boat position.

    Returns:
        dict: {latitude, longitude} or None
    """
    result = get_signalk_value('navigation/position/value', token)
    return result


def get_rode_deployed(token=None):
    """Get current rode deployed length.

    Returns:
        float: Rode length in meters, or None
    """
    result = get_signalk_value('navigation/anchor/rodeDeployed', token)
    if result:
        return result.get('value')
    return None


def get_anchor_position(token=None):
    """Get anchor position.

    Returns:
        dict: {latitude, longitude, altitude} or None
    """
    result = get_signalk_value('navigation/anchor/position', token)
    if result:
        return result.get('value')
    return None


# =============================================================================
# SignalK API - Writing
# =============================================================================

def put_signalk_value(path, value, token=None):
    """PUT a value to SignalK API.

    Args:
        path: SignalK path (e.g., 'navigation.anchor.command')
        value: Value to send
        token: Optional auth token

    Returns:
        bool: True if successful
    """
    if token is None:
        token = get_auth_token()
    if not token:
        return False

    try:
        url = f"{BASE_URL}/signalk/v1/api/vessels/self/{path}"
        data = json.dumps({"value": value}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return True
    except Exception as e:
        return False


def send_anchor_command(command, token=None):
    """Send a command to the anchor system.

    Args:
        command: Command string (e.g., 'autoDrop', 'autoRetrieve', 'stop')
        token: Optional auth token

    Returns:
        bool: True if successful
    """
    return put_signalk_value('navigation/anchor/command', command, token)


# =============================================================================
# Simulation Control
# =============================================================================

def get_simulation_state(token=None):
    """Get current simulation state including forces and boat state.

    Returns:
        dict: Full simulation state or None
    """
    if token is None:
        token = get_auth_token()
    if not token:
        return None

    try:
        url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/simulation/state"
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read())
    except:
        return None


def configure_simulation(config, token=None):
    """Update simulation configuration.

    Args:
        config: Dict with config updates (e.g., {'wind': {'initialSpeed': 15}})
        token: Optional auth token

    Returns:
        dict: New config if successful, None otherwise
    """
    if token is None:
        token = get_auth_token()
    if not token:
        return None

    try:
        url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/simulation/config"
        data = json.dumps(config).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read())
    except Exception as e:
        print(f"Config error: {e}")
        return None


def configure_environment(wind_speed, depth, token=None):
    """Configure wind speed and depth for testing.

    Args:
        wind_speed: Wind speed in knots
        depth: Water depth in meters
        token: Optional auth token

    Returns:
        bool: True if successful
    """
    config = {
        "wind": {
            "initialSpeed": wind_speed,
            "initialDirection": 180
        },
        "environment": {
            "depth": depth
        }
    }
    return configure_simulation(config, token) is not None


def reset_simulation(token=None):
    """Reset simulation to initial state.

    Returns:
        bool: True if successful
    """
    if token is None:
        token = get_auth_token()
    if not token:
        return False

    try:
        url = f"{BASE_URL}/plugins/signalk-anchoralarmconnector/simulation/reset"
        req = urllib.request.Request(url, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')
        with urllib.request.urlopen(req, timeout=5) as response:
            return True
    except:
        return False


# =============================================================================
# Chain Controller (ESP32)
# =============================================================================

def check_chain_controller():
    """Check if chain controller (ESP32) is responding via SignalK.

    Returns:
        tuple: (bool success, str message)
    """
    try:
        token = get_auth_token()
        if not token:
            return False, "No auth token"

        result = get_signalk_value('navigation/anchor/rodeDeployed', token)
        if result:
            source = result.get('$source', '')
            if source.startswith('ws.'):
                return True, f"Connected via {source[:20]}..."
            else:
                return False, f"Unexpected source: {source}"
        return False, "No rode deployed data"
    except Exception as e:
        return False, str(e)


def restart_chain_controller(wait_time=15):
    """Restart the ESP32 chain controller.

    Args:
        wait_time: Seconds to wait for restart (default 15)

    Returns:
        bool: True if successfully restarted and reconnected
    """
    try:
        print(f"Restarting chain controller at {ESP32_IP}...")
        url = f"http://{ESP32_IP}/api/device/restart"
        req = urllib.request.Request(url, method='POST')
        with urllib.request.urlopen(req, timeout=5) as response:
            pass

        print(f"Waiting {wait_time}s for ESP32 to restart...")
        time.sleep(wait_time)

        # Verify reconnection
        for attempt in range(5):
            ok, msg = check_chain_controller()
            if ok:
                print(f"✓ Chain controller reconnected: {msg}")
                return True
            time.sleep(3)

        print("✗ Chain controller did not reconnect after restart")
        return False
    except Exception as e:
        print(f"✗ Failed to restart chain controller: {e}")
        return False


def ensure_chain_controller():
    """Ensure chain controller is responsive, restart if needed.

    Returns:
        bool: True if controller is responsive
    """
    ok, msg = check_chain_controller()
    if ok:
        return True

    print(f"! Chain controller not responding: {msg}")
    return restart_chain_controller()


# =============================================================================
# Server Verification
# =============================================================================

def verify_server():
    """Verify SignalK server and plugin are running.

    Returns:
        bool: True if server is ready
    """
    try:
        # Check server responds
        urllib.request.urlopen(f"{BASE_URL}/signalk", timeout=5).close()

        # Check we can authenticate
        token = get_auth_token()
        return token is not None
    except:
        return False


def verify_simulation():
    """Verify simulation is running.

    Returns:
        bool: True if simulation is active
    """
    state = get_simulation_state()
    return state is not None and state.get('running', False)


# =============================================================================
# Coordinate Utilities
# =============================================================================

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate approximate distance in meters between two coordinates.

    Uses simple flat-earth approximation (accurate for short distances).

    Returns:
        float: Distance in meters
    """
    dlat = (lat2 - lat1) / METERS_TO_LAT
    dlon = (lon2 - lon1) / METERS_TO_LON
    return (dlat**2 + dlon**2)**0.5


def calculate_bearing(lat1, lon1, lat2, lon2):
    """Calculate bearing from point 1 to point 2.

    Returns:
        float: Bearing in degrees (0-360)
    """
    import math
    dlat = (lat2 - lat1) / METERS_TO_LAT
    dlon = (lon2 - lon1) / METERS_TO_LON
    bearing = math.degrees(math.atan2(dlon, dlat))
    return (bearing + 360) % 360

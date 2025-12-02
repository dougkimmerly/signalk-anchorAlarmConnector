#!/usr/bin/env python3
"""
AutoDrop and AutoRetrieve Testing Suite

Tests anchor deployment and retrieval at multiple wind speeds.
Records: position, heading, chain deployed, slack, wind direction, and other metrics.
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime
import os

# Global token for authenticated requests
auth_token = None

# Stage tracking for clear test progression visibility
current_stage = None
stage_start_time = None

STAGES = {
    'SETUP': 'Environment setup and verification',
    'AUTODROP_15': 'AutoDrop test at 15kn wind',
    'SETTLE_15': 'Observing boat behavior at anchor (15kn)',
    'AUTORETRIEVE_15': 'AutoRetrieve test at 15kn wind',
    'WAIT_RETRIEVE_15': 'Waiting after retrieval (15kn)',
    'RESET_15': 'Resetting chain for next test (15kn)',
    'AUTODROP_10': 'AutoDrop test at 10kn wind',
    'SETTLE_10': 'Observing boat behavior at anchor (10kn)',
    'AUTORETRIEVE_10': 'AutoRetrieve test at 10kn wind',
    'WAIT_RETRIEVE_10': 'Waiting after retrieval (10kn)',
    'RESET_10': 'Resetting chain for next test (10kn)',
    'AUTODROP_5': 'AutoDrop test at 5kn wind',
    'SETTLE_5': 'Observing boat behavior at anchor (5kn)',
    'AUTORETRIEVE_5': 'AutoRetrieve test at 5kn wind',
    'WAIT_RETRIEVE_5': 'Waiting after retrieval (5kn)',
    'RESET_5': 'Resetting chain for final setup',
    'COMPLETE': 'Test suite complete',
}

def report_stage(stage_key):
    """Report a stage change with timestamp"""
    global current_stage, stage_start_time
    current_stage = stage_key
    stage_start_time = time.time()

    if stage_key in STAGES:
        stage_name = STAGES[stage_key]
        print(f"\n{'▶'*40}")
        print(f"STAGE: {stage_name}")
        print(f"{'▶'*40}\n")
    else:
        print(f"\n[STAGE] Unknown stage: {stage_key}\n")

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
                print(f"✗ No token in response: {result}")
                return False
    except Exception as e:
        print(f"Error authenticating: {e}")
        return False

def stop_controller():
    """Stop the chain controller and verify it's stopped"""
    global auth_token
    if not auth_token:
        print("Error: Not authenticated - cannot stop controller")
        return False

    try:
        # Send stop command with Bearer token
        url = f"http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/command"
        data = json.dumps({"value": "stop"}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {auth_token}')

        with urllib.request.urlopen(req, timeout=2) as response:
            print(f"✓ STOP command sent to controller")
    except Exception as e:
        print(f"Warning: Error sending stop command: {e}")
        # Continue anyway - controller may be stopped

    time.sleep(1)

    # Verify controller is stopped
    try:
        url = "http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/chainDirection"
        with urllib.request.urlopen(url, timeout=2) as response:
            result = json.loads(response.read())
            chain_dir = result.get('value', 'unknown')
            if chain_dir not in ['down', 'up']:
                print(f"✓ Controller is stopped (chainDirection: {chain_dir})")
                return True
            else:
                print(f"⚠ Controller still active (chainDirection: {chain_dir})")
                return False
    except Exception as e:
        print(f"Warning: Error verifying stop: {e}")
        return False

def get_signalk_data(path=""):
    """Get data from SignalK server"""
    try:
        url = f"http://localhost:80/signalk/v1/api/vessels/self{path}"
        with urllib.request.urlopen(url, timeout=3) as response:
            return json.loads(response.read())
    except urllib.error.URLError as e:
        return None
    except (json.JSONDecodeError, Exception):
        return None

def send_signalk_command(path, value):
    """Send a command to SignalK server via PUT request"""
    global auth_token
    if not auth_token:
        print("Error: Not authenticated")
        return False

    try:
        # Convert dots to slashes in path (e.g., "navigation.anchor.command" -> "navigation/anchor/command")
        clean_path = path.replace('.', '/')
        url = f"http://localhost:80/signalk/v1/api/vessels/self/{clean_path}"
        data = json.dumps({"value": value}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {auth_token}')

        with urllib.request.urlopen(req, timeout=2) as response:
            return True
    except (urllib.error.URLError, Exception) as e:
        print(f"Error sending SignalK command: {e}")
        return False

def reset_velocity_tracking():
    """Reset velocity tracking state for next test"""
    global _last_position, _last_position_time
    _last_position = None
    _last_position_time = None

def reset_anchor():
    """Reset anchor: stop command, then reset rodeDeployed to 0"""
    global auth_token
    if not auth_token:
        print("Error: Not authenticated")
        return False

    try:
        # Step 1: Reset velocity tracking for new test
        reset_velocity_tracking()

        # Step 2: Stop the chain controller (stops any active autoRetrieve or autoDrop)
        print("   [Reset] Stopping chain controller...", end="", flush=True)
        if not send_signalk_command("navigation.anchor.command", "stop"):
            print(" ✗ (continuing anyway)")
        else:
            print(" ✓")

        time.sleep(1)

        # Step 2: Reset rodeDeployed to 0 by sending value of 1
        print("   [Reset] Resetting rodeDeployed to 0...", end="", flush=True)
        if not send_signalk_command("navigation.anchor.rodeDeployed", 1):
            print(" ✗")
            return False
        else:
            print(" ✓")

        # Step 3: Verify it was reset (with timeout protection)
        print("   [Reset] Verifying reset...", end="", flush=True)
        time.sleep(1)

        # Try verification with timeout (max 60 seconds total - allow extra time for ESP32 to process)
        # Keep retrying the reset if rode is still deployed
        verify_success = False
        verify_timeout = time.time() + 60
        attempt = 0
        while time.time() < verify_timeout and attempt < 15:
            attempt += 1
            try:
                # Get anchor data directly
                nav = get_signalk_data("/navigation/anchor")
                if nav and 'rodeDeployed' in nav:
                    current_rode = nav['rodeDeployed'].get('value')
                    if current_rode is not None:
                        # Success: rode is reset to 0 or very close to 0
                        if current_rode <= 0.5:
                            print(f" ✓ (rode={current_rode:.1f}m after {attempt} checks)")
                            verify_success = True
                            break
                        else:
                            # Rode still deployed - send reset command again
                            if attempt % 3 == 0:  # Re-send reset every 3 attempts
                                print(f"\n   [Reset] Rode still at {current_rode:.1f}m, retrying reset...", end="", flush=True)
                                send_signalk_command("navigation.anchor.rodeDeployed", 1)
                                print(" ✓", end="", flush=True)
            except Exception:
                pass  # Retry on error

            if time.time() < verify_timeout:
                time.sleep(1)

        if verify_success:
            return True
        else:
            print(" ✗ (could not verify reset)")
            return False

    except Exception:
        print(f" ✗ Error during reset")
        return False

def autodrop_anchor():
    """Issue autoDrop command"""
    return send_signalk_command("navigation.anchor.command", "autoDrop")

def stop_anchor():
    """Issue STOP command to halt active deployment/retrieval"""
    return send_signalk_command("navigation.anchor.command", "STOP")

def test_stop_deployment():
    """Test stopping an active deployment mid-way"""
    print("\n" + "="*70)
    print("TESTING STOP COMMAND - STOPPING ACTIVE DEPLOYMENT")
    print("="*70)

    # Step 1: Start a deployment
    print("\n[Step 1] Starting deployment with 'lower10' command...", end="", flush=True)
    if not send_signalk_command("navigation.anchor.command", "lower10"):
        print(" ✗ Failed to send lower command")
        return False
    print(" ✓")

    # Step 2: Wait for deployment to begin
    print("[Step 2] Waiting for deployment to start (2 seconds)...", end="", flush=True)
    time.sleep(2)
    print(" ✓")

    # Step 3: Check current rode deployed
    nav = get_signalk_data("/navigation/anchor")
    if nav and 'rodeDeployed' in nav:
        rode_before = nav['rodeDeployed'].get('value', 0)
        print(f"\n[Step 3] Rode deployed before STOP: {rode_before:.2f}m")
    else:
        print("\n[Step 3] Could not read rode deployed")
        return False

    # Step 4: Issue STOP command while deploying
    print("[Step 4] Issuing STOP command to halt deployment...", end="", flush=True)
    if not stop_anchor():
        print(" ✗ Failed to send STOP command")
        return False
    print(" ✓")
    time.sleep(1)

    # Step 5: Check if rode stopped increasing
    nav = get_signalk_data("/navigation/anchor")
    if nav and 'rodeDeployed' in nav:
        rode_after = nav['rodeDeployed'].get('value', 0)
        print(f"[Step 5] Rode deployed after STOP: {rode_after:.2f}m")

        # Verify it actually stopped (should not have deployed full 10m)
        deployed = rode_after - rode_before
        print(f"[Step 6] Amount deployed before stop: {deployed:.2f}m (expected < 10m)")

        if deployed < 10.0 and deployed > 0.1:  # Some deployment but not all 10m
            print("✓ STOP command successfully halted deployment")
            return True
        elif deployed >= 10.0:
            print("✗ Deployment continued despite STOP command (deployed 10m+)")
            return False
        else:
            print("✗ No deployment occurred at all")
            return False
    else:
        print("[Step 5] Could not verify rode after STOP")
        return False

def autoretrieve_anchor():
    """Issue autoRetrieve command"""
    return send_signalk_command("navigation.anchor.command", "autoRetrieve")

def motor_forward():
    """Start motor moving forward toward anchor (via simulator endpoint)"""
    global auth_token
    if not auth_token:
        if not get_auth_token():
            return False
    try:
        url = "http://localhost:80/plugins/signalk-anchorAlarmConnector/motorforward"
        req = urllib.request.Request(url, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {auth_token}')
        with urllib.request.urlopen(req, timeout=2) as response:
            return True
    except Exception as e:
        return False

def motor_backward():
    """Start motor moving backward away from anchor (via simulator endpoint)"""
    global auth_token
    if not auth_token:
        if not get_auth_token():
            return False
    try:
        url = "http://localhost:80/plugins/signalk-anchorAlarmConnector/motorbackward"
        req = urllib.request.Request(url, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {auth_token}')
        with urllib.request.urlopen(req, timeout=2) as response:
            return True
    except Exception as e:
        return False

def motor_stop():
    """Stop motor (via simulator endpoint)"""
    global auth_token
    if not auth_token:
        if not get_auth_token():
            return False
    try:
        url = "http://localhost:80/plugins/signalk-anchorAlarmConnector/motorstop"
        req = urllib.request.Request(url, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {auth_token}')
        with urllib.request.urlopen(req, timeout=2) as response:
            return True
    except Exception as e:
        return False

class SpeedMonitor:
    """Monitors boat speed and auto-engages motor if below threshold"""

    def __init__(self, operation_type='deploy', min_speed_threshold=0.2):
        """
        Initialize speed monitor

        Args:
            operation_type: Either 'deploy' (backward) or 'retrieve' (forward)
            min_speed_threshold: Minimum boat speed in m/s before motor engages (default 0.2 m/s)
        """
        self.operation_type = operation_type  # 'deploy' or 'retrieve'
        self.min_speed_threshold = min_speed_threshold
        self.motor_active = False
        self.motor_engagement_count = 0
        self.motor_engagement_times = []
        self.last_engagement_time = None

    def check_and_engage(self, metrics, current_time):
        """
        Check boat speed and auto-engage motor if needed.
        Motor direction is based on operation type (deploy=backward, retrieve=forward)

        Returns: (motor_engaged, engagement_info_str)
        """
        if not metrics:
            return False, ""

        boat_speed = metrics.get('boat_speed', 0)

        # If boat speed is too low, engage motor in direction appropriate for operation
        if boat_speed < self.min_speed_threshold:
            if not self.motor_active:
                if self.operation_type == 'deploy':
                    motor_backward()  # Move away from anchor during deployment
                    direction = "backward (away)"
                else:  # retrieve
                    motor_forward()   # Move toward anchor during retrieval
                    direction = "forward (toward)"

                self.motor_active = True
                self.motor_engagement_count += 1
                self.motor_engagement_times.append(current_time)
                self.last_engagement_time = current_time
                return True, f"Motor engaged {direction} anchor (speed={boat_speed:.2f}m/s < {self.min_speed_threshold}m/s)"
        else:
            # Speed is sufficient, can stop motor if it was engaged
            if self.motor_active and boat_speed > (self.min_speed_threshold + 0.1):
                motor_stop()
                self.motor_active = False
                return True, f"Motor disengaged (speed sufficient: {boat_speed:.2f}m/s)"

        return False, ""

# Global state for velocity calculation (test environment only)
_last_position = None
_last_position_time = None

def calculate_local_velocity(current_pos, current_time):
    """Calculate velocity from position changes (local to test environment)"""
    global _last_position, _last_position_time

    if _last_position is None or _last_position_time is None:
        # First measurement
        _last_position = current_pos
        _last_position_time = current_time
        return {'vel_x': 0, 'vel_y': 0, 'boat_speed': 0}

    # Calculate time delta in seconds
    time_delta = (current_time - _last_position_time).total_seconds()
    if time_delta <= 0:
        return {'vel_x': 0, 'vel_y': 0, 'boat_speed': 0}

    # Convert lat/lon to approximate meters (using constants from testSimulation.js)
    METERS_TO_LAT = 0.000009
    METERS_TO_LON = 0.0000125

    lat_delta_meters = (current_pos['latitude'] - _last_position['latitude']) / METERS_TO_LAT
    lon_delta_meters = (current_pos['longitude'] - _last_position['longitude']) / METERS_TO_LON

    # Calculate velocity in m/s
    vel_x = lon_delta_meters / time_delta
    vel_y = lat_delta_meters / time_delta
    boat_speed = (vel_x**2 + vel_y**2)**0.5

    # Update for next measurement
    _last_position = current_pos
    _last_position_time = current_time

    return {'vel_x': vel_x, 'vel_y': vel_y, 'boat_speed': boat_speed}

def get_current_metrics():
    """Get current position, heading, and chain metrics with locally calculated velocity"""
    data = get_signalk_data()
    if not data:
        return None

    nav = data.get('navigation', {})
    env = data.get('environment', {})

    pos = nav.get('position', {}).get('value', {})

    if not isinstance(pos, dict) or pos.get('latitude') is None:
        return None

    # Calculate velocity locally from position changes
    current_time = datetime.now()
    current_pos = {'latitude': pos.get('latitude'), 'longitude': pos.get('longitude')}
    velocity_data = calculate_local_velocity(current_pos, current_time)

    return {
        'timestamp': current_time.isoformat(),
        'latitude': pos.get('latitude'),
        'longitude': pos.get('longitude'),
        'heading': nav.get('headingTrue', {}).get('value', 0),
        'heading_magnetic': nav.get('headingMagnetic', {}).get('value', 0),
        'distance': nav.get('anchor', {}).get('distanceFromBow', {}).get('value', 0),
        'rode_deployed': nav.get('anchor', {}).get('rodeDeployed', {}).get('value', 0),
        'chain_slack': nav.get('anchor', {}).get('chainSlack', {}).get('value', 0),
        'wind_speed': env.get('wind', {}).get('speedTrue', {}).get('value', 0),
        'wind_direction': env.get('wind', {}).get('directionTrue', {}).get('value', 0),
        'depth': env.get('depth', {}).get('belowSurface', {}).get('value', 0),
        'velocity_x': velocity_data['vel_x'],
        'velocity_y': velocity_data['vel_y'],
        'boat_speed': velocity_data['boat_speed'],
    }

def record_deployment(wind_speed_kn, duration_seconds=300):
    """Record autoDrop deployment at specified wind speed"""
    print(f"\n{'='*70}")
    print(f"AUTODROP TEST - {wind_speed_kn}kn WIND")
    print(f"{'='*70}")

    # Prepare for autoDrop (anchor should already be at 0m from previous reset)
    print(f"\nPreparing for autoDrop test...")
    time.sleep(1)

    # Issue autoDrop command
    print(f"Issuing autoDrop command...")
    if not autodrop_anchor():
        print("✗ Failed to send autoDrop command")
        return None

    print(f"✓ autoDrop started - recording for {duration_seconds}s at {wind_speed_kn}kn wind")
    print(f"   Monitoring boat speed - motor will auto-engage if speed drops below threshold")

    # Record data with speed monitoring
    samples = []
    start_time = time.time()
    last_print = start_time
    speed_monitor = SpeedMonitor(operation_type='deploy', min_speed_threshold=0.2)
    last_motor_action = start_time
    consecutive_none_count = 0
    max_consecutive_none = 10  # Exit early if we get 10 consecutive None responses

    while time.time() - start_time < duration_seconds:
        metrics = get_current_metrics()
        elapsed = time.time() - start_time
        current_time = time.time()

        if metrics:
            consecutive_none_count = 0  # Reset counter when we get valid data
            metrics['time_sec'] = elapsed
            samples.append(metrics)

            # Check and auto-engage motor every 2 seconds
            if current_time - last_motor_action >= 2:
                engaged, info = speed_monitor.check_and_engage(metrics, elapsed)
                if engaged:
                    print(f"  {elapsed:.0f}s: [AUTO] {info}")
                last_motor_action = current_time

        else:
            consecutive_none_count += 1
            # If we can't get data after 10 tries, exit early
            if consecutive_none_count >= max_consecutive_none:
                print(f"  {elapsed:.0f}s: ⚠ No valid data for {max_consecutive_none}s, ending collection early")
                break

        # Print status every 10 seconds
        if elapsed - last_print >= 10:
            last_print = elapsed
            if metrics and metrics.get('time_sec') is not None and all(v is not None for v in [metrics.get('distance'), metrics.get('rode_deployed'),
                                                         metrics.get('chain_slack'), metrics.get('heading'),
                                                         metrics.get('wind_speed'), metrics.get('wind_direction')]):
                motor_status = "MOTOR ON" if speed_monitor.motor_active else "motor off"
                print(f"  {elapsed:.0f}s: "
                      f"Speed={metrics['boat_speed']:.2f}m/s({motor_status}) "
                      f"Dist={metrics['distance']:.1f}m "
                      f"Rode={metrics['rode_deployed']:.1f}m "
                      f"Slack={metrics['chain_slack']:.1f}m")
            else:
                print(f"  {elapsed:.0f}s: (waiting for valid position data)")

        time.sleep(1)

    if not samples:
        print("✗ No data collected")
        return None

    print(f"\n✓ Recording complete - {len(samples)} samples collected")

    # Save data
    filename = f"autodrop_{wind_speed_kn}kn_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump({
            'test_type': 'autoDrop',
            'wind_speed_kn': wind_speed_kn,
            'duration_seconds': duration_seconds,
            'samples': samples
        }, f, indent=2)

    print(f"✓ Data saved to {filename}")

    return {
        'wind_speed': wind_speed_kn,
        'filename': filename,
        'samples': samples
    }

def check_deployment_complete(samples, target_scope=5.0, expected_depth=3.0, bow_height=2.0):
    """
    Check if deployment reached target scope ratio.
    Returns (is_complete, final_rode, final_depth, final_scope, target_scope)

    Target: 5:1 scope (rode / (depth + bow_height) >= 5.0)
    Scope accounts for vertical distance from bow to anchor
    """
    if not samples:
        return False, 0, expected_depth, 0, target_scope

    final_rode = samples[-1].get('rode_deployed', 0)
    final_depth = samples[-1].get('depth', expected_depth)

    if final_depth <= 0:
        final_depth = expected_depth

    # Scope = rode / (depth + bow_height)
    # This represents the actual vertical distance from bow to anchor
    scope_denominator = final_depth + bow_height
    final_scope = final_rode / scope_denominator if scope_denominator > 0 else 0

    # Deployment is complete if scope >= target
    is_complete = final_scope >= target_scope

    return is_complete, final_rode, final_depth, final_scope, target_scope

def analyze_deployment(deployment_data):
    """Analyze deployment test results"""
    if not deployment_data or not deployment_data['samples']:
        print("✗ No data to analyze")
        return

    samples = deployment_data['samples']
    wind_speed = deployment_data['wind_speed']

    print(f"\n{'-'*70}")
    print(f"ANALYSIS - {wind_speed}kn WIND DEPLOYMENT")
    print(f"{'-'*70}")

    # Extract boat speeds
    boat_speeds = [s['boat_speed'] for s in samples if s.get('boat_speed') is not None and isinstance(s.get('boat_speed'), (int, float))]
    if boat_speeds:
        avg_speed = sum(boat_speeds) / len(boat_speeds)
        max_speed = max(boat_speeds)
        min_speed = min(boat_speeds)
        low_speed_count = sum(1 for s in boat_speeds if s < 0.2)

        print(f"\nBoat Speed Analysis:")
        print(f"  Average speed: {avg_speed:.3f} m/s")
        print(f"  Max speed: {max_speed:.3f} m/s")
        print(f"  Min speed: {min_speed:.3f} m/s")
        print(f"  Low speed periods (<0.2 m/s): {low_speed_count} samples")

    # Extract metrics and filter out None values
    distances = [s['distance'] for s in samples if s.get('distance') is not None and isinstance(s.get('distance'), (int, float))]
    rodes = [s['rode_deployed'] for s in samples if s.get('rode_deployed') is not None and isinstance(s.get('rode_deployed'), (int, float))]
    slacks = [s['chain_slack'] for s in samples if s.get('chain_slack') is not None and isinstance(s.get('chain_slack'), (int, float))]
    headings = [s['heading'] for s in samples if s.get('heading') is not None and isinstance(s.get('heading'), (int, float))]
    positions = [(s['latitude'], s['longitude']) for s in samples if s.get('latitude') is not None and s.get('longitude') is not None]

    print(f"\nDistance Metrics:")
    if distances and len(distances) > 0:
        print(f"  Initial: {distances[0]:.1f}m")
        print(f"  Final: {distances[-1]:.1f}m")
        print(f"  Max: {max(distances):.1f}m")
        print(f"  Change: {distances[-1] - distances[0]:+.1f}m")
    else:
        print(f"  No valid distance data")

    print(f"\nChain Deployment:")
    if rodes and len(rodes) > 0:
        print(f"  Initial rode: {rodes[0]:.1f}m")
        print(f"  Final rode: {rodes[-1]:.1f}m")
        print(f"  Deployed: {rodes[-1] - rodes[0]:.1f}m")
    else:
        print(f"  No valid rode data")

    print(f"\nSlack Analysis:")
    if slacks and len(slacks) > 0:
        print(f"  Min: {min(slacks):.1f}m")
        print(f"  Max: {max(slacks):.1f}m")
        print(f"  Final: {slacks[-1]:.1f}m")
        print(f"  Negative instances: {sum(1 for s in slacks if s < 0)}")
    else:
        print(f"  No valid slack data")

    if slacks and any(s < 0 for s in slacks):
        print(f"  ✗ ISSUE: Slack went negative!")
    elif slacks and len(slacks) > 0:
        print(f"  ✓ Slack remained positive")

    print(f"\nHeading Consistency:")
    if headings and len(headings) > 0:
        heading_deg = [(h * 180 / 3.14159) % 360 for h in headings]
        print(f"  Initial: {heading_deg[0]:.1f}°")
        print(f"  Final: {heading_deg[-1]:.1f}°")
        print(f"  Variation: {max(heading_deg) - min(heading_deg):.1f}°")
    else:
        print(f"  No valid heading data")

    # Check deployment rate
    if len(samples) > 1 and len(distances) > 0 and len(rodes) > 0:
        time_elapsed = samples[-1].get('time_sec', 0) - samples[0].get('time_sec', 0)
        rode_deployed = rodes[-1] - rodes[0]
        distance_change = distances[-1] - distances[0]

        deployment_rate = rode_deployed / time_elapsed if time_elapsed > 0 else 0
        drift_rate = distance_change / time_elapsed if time_elapsed > 0 else 0

        print(f"\nDrift Analysis:")
        print(f"  Distance change: {distance_change:+.1f}m")
        print(f"  Time elapsed: {time_elapsed:.0f}s")
        print(f"  Drift rate: {drift_rate:.3f} m/s")

        print(f"\nDeployment Rate Analysis:")
        print(f"  Rode deployed: {rode_deployed:.1f}m")
        print(f"  Deployment rate: {deployment_rate:.3f} m/s")
        print(f"  Expected drift rate for {wind_speed}kn: ~{wind_speed/20:.2f} m/s")
    else:
        print(f"\nInsufficient data for rate analysis")

def setup_environment():
    """Setup and verify test environment before running tests"""
    print(f"\n{'='*70}")
    print("SETTING UP TEST ENVIRONMENT")
    print(f"{'='*70}")

    # Step 1: Verify SignalK is accessible
    print("\n[1/6] Verifying SignalK connection...", end="", flush=True)
    if get_signalk_data():
        print(" ✓")
    else:
        print(" ✗")
        return False

    # Step 2: Verify ESP device is connected and responding
    print("[2/6] Verifying ESP device is connected...", end="", flush=True)
    if get_current_metrics():
        print(" ✓")
    else:
        print(" ✗")
        return False

    # Step 3: Authenticate
    print("[3/6] Authenticating...", end="", flush=True)
    if get_auth_token():
        print(" ✓")
    else:
        print(" ✗")
        return False

    # Step 4: Stop any active anchor command and fully retract
    print("[4/6] Stopping chain controller and retracting...")
    if not reset_anchor():
        print("      ✗ Failed to reset anchor")
        return False
    print("      ✓ Anchor reset complete")

    # Step 5: Verify final state (rode should be at or near 0)
    print("[5/6] Verifying final state...", end="", flush=True)
    time.sleep(1)
    metrics = get_current_metrics()
    if metrics:
        rode = metrics.get('rode_deployed', 0)
        distance = metrics.get('distance', 0)

        if rode < 2:  # Rode should be retracted to near 0
            print(f" ✓ (Rode={rode:.1f}m)")
        else:
            print(f" ✗ (Rode still at {rode:.1f}m - not fully retracted)")
            return False
    else:
        print(" ✗")
        return False

    print(f"\n{'='*70}")
    print("ENVIRONMENT READY - STARTING TESTS")
    print(f"{'='*70}")
    return True


def main():
    """Main test entry point"""
    print(f"\n{'='*70}")
    print("AUTODROP AND AUTORETRIEVE TEST SUITE")
    print(f"{'='*70}")
    print(f"Started: {datetime.now().isoformat()}")

    # Setup and verify environment
    report_stage('SETUP')
    if not setup_environment():
        print("\n✗ Environment setup failed - aborting tests")
        return False

    # Test at different wind speeds
    print(f"\n{'='*70}")
    print("AUTHENTICATING FOR TESTS")
    print(f"{'='*70}")
    if not get_auth_token():
        print("✗ Failed to authenticate")
        return False

    # Test at different wind speeds
    wind_speeds = [15, 10, 5]  # knots
    results = []

    for wind_speed in wind_speeds:
        print(f"\n\n{'#'*70}")
        print(f"# WIND SPEED: {wind_speed}kn")
        print(f"{'#'*70}")

        # AutoDrop test (5 minutes)
        stage_key = f'AUTODROP_{wind_speed}'
        report_stage(stage_key)
        deployment = record_deployment(wind_speed, duration_seconds=300)

        # Check if deployment is complete
        deployment_complete = False
        if deployment:
            is_complete, final_rode, final_depth, final_scope, target_scope = check_deployment_complete(
                deployment['samples'], target_scope=5.0, expected_depth=3.0, bow_height=2.0
            )
            if is_complete:
                deployment_complete = True
                print(f"\n✓ DEPLOYMENT COMPLETE: Scope {final_scope:.2f}:1 (rode={final_rode:.1f}m, depth={final_depth:.1f}m, target={target_scope:.1f}:1)")
                analyze_deployment(deployment)
                results.append(deployment)
            else:
                print(f"\n✗ DEPLOYMENT INCOMPLETE: Scope {final_scope:.2f}:1 (rode={final_rode:.1f}m, depth={final_depth:.1f}m, target={target_scope:.1f}:1)")
                print(f"✗ Resetting system and retrying test suite...")

        if not deployment_complete:
            # Reset entire system and restart tests
            print(f"\nResetting system for retry...")
            reset_anchor()
            time.sleep(3)
            # Skip remaining stages for this wind speed and continue to retry
            print(f"Retrying all tests...")
            wind_speeds = [15, 10, 5]  # Reset to start over
            continue

        # Wait 300 seconds to observe boat settling at anchor
        settle_stage = f'SETTLE_{wind_speed}'
        report_stage(settle_stage)
        print(f"\nWaiting 300 seconds to observe boat behavior at anchor...")
        for i in range(300):
            time.sleep(1)
            if (i + 1) % 30 == 0:
                print(f"  {i + 1}s elapsed...")

        # AutoRetrieve test (up to 5 minutes)
        retrieve_stage = f'AUTORETRIEVE_{wind_speed}'
        report_stage(retrieve_stage)
        print(f"\nIssuing autoRetrieve command...")
        if autoretrieve_anchor():
            print(f"✓ autoRetrieve started - monitoring for 5 minutes")
            print(f"   Monitoring boat speed - motor will auto-engage if needed")

            retrieve_samples = []
            start_time = time.time()
            last_print = start_time
            speed_monitor = SpeedMonitor(operation_type='retrieve', min_speed_threshold=0.15)
            last_motor_action = start_time
            consecutive_none_count = 0
            max_consecutive_none = 10  # Exit early if we get 10 consecutive None responses

            while time.time() - start_time < 300:
                metrics = get_current_metrics()
                elapsed = time.time() - start_time
                current_time = time.time()

                if metrics:
                    consecutive_none_count = 0  # Reset counter when we get valid data
                    metrics['time_sec'] = elapsed
                    retrieve_samples.append(metrics)

                    # Check and auto-engage motor every 2 seconds during retrieval
                    if current_time - last_motor_action >= 2:
                        engaged, info = speed_monitor.check_and_engage(metrics, elapsed)
                        if engaged:
                            print(f"  {elapsed:.0f}s: [AUTO] {info}")
                        last_motor_action = current_time

                else:
                    consecutive_none_count += 1
                    # If we can't get data after 10 tries, exit early
                    if consecutive_none_count >= max_consecutive_none:
                        print(f"  {elapsed:.0f}s: ⚠ No valid data for {max_consecutive_none}s, ending collection early")
                        break

                # Print status every 10 seconds
                if elapsed - last_print >= 10:
                    last_print = elapsed
                    if metrics:
                        motor_status = "MOTOR ON" if speed_monitor.motor_active else "motor off"
                        print(f"  {elapsed:.0f}s: "
                              f"Speed={metrics['boat_speed']:.2f}m/s({motor_status}) "
                              f"Dist={metrics['distance']:.1f}m "
                              f"Rode={metrics['rode_deployed']:.1f}m "
                              f"Slack={metrics['chain_slack']:.1f}m")
                    else:
                        print(f"  {elapsed:.0f}s: (waiting for valid position data)")

                time.sleep(1)

            # Save retrieval data
            if retrieve_samples:
                filename = f"autoretrieve_{wind_speed}kn_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filename, 'w') as f:
                    json.dump({
                        'test_type': 'autoRetrieve',
                        'wind_speed_kn': wind_speed,
                        'samples': retrieve_samples
                    }, f, indent=2)
                print(f"✓ Retrieval data saved to {filename}")
        else:
            print("✗ Failed to start autoRetrieve")

        # Wait 30 seconds after retrieval, then reset for next test
        wait_stage = f'WAIT_RETRIEVE_{wind_speed}'
        report_stage(wait_stage)
        print(f"Waiting 30 seconds after retrieval...")
        for i in range(30):
            time.sleep(1)
            if (i + 1) % 10 == 0:
                print(f"  {i + 1}s elapsed...")

        # Reset chain to 0m for next test
        reset_stage = f'RESET_{wind_speed}'
        report_stage(reset_stage)
        print(f"Resetting chain to 0m for next test...")
        reset_anchor()

        # Brief pause before next wind speed test
        if wind_speed != wind_speeds[-1]:
            print(f"\nPreparing for next wind speed test...")
            time.sleep(5)
    
    report_stage('COMPLETE')
    print(f"Completed: {datetime.now().isoformat()}")
    print(f"Tests run: {len(results)}")

    return True

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)

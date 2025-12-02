#!/usr/bin/env python3
"""
Quick test to validate physics changes
Connects to SignalK server and analyzes boat behavior
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime

# Global token for authenticated requests
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
            if auth_token:
                print(f"✓ Authentication successful")
                return True
            else:
                print(f"✗ No token in response: {result}")
                return False
    except Exception as e:
        print(f"Error authenticating: {e}")
        return False

def get_signalk_data(path=""):
    """Get data from SignalK server"""
    try:
        url = f"http://localhost:80/signalk/v1/api/vessels/self{path}"
        with urllib.request.urlopen(url, timeout=2) as response:
            return json.loads(response.read())
    except (urllib.error.URLError, json.JSONDecodeError, Exception) as e:
        print(f"Error getting SignalK data: {e}")
        return None

def send_signalk_command(path, value):
    """Send a command to SignalK server via PUT request"""
    global auth_token
    if not auth_token:
        print("Error: Not authenticated")
        return False

    try:
        url = f"http://localhost:80/signalk/v1/api/vessels/self/{path}"
        data = json.dumps({"value": value}).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {auth_token}')

        with urllib.request.urlopen(req, timeout=2) as response:
            return True
    except (urllib.error.URLError, Exception) as e:
        print(f"Error sending SignalK command: {e}")
        return False

def test_server_connection():
    """Test if server is accessible"""
    print("\n" + "=" * 70)
    print("TESTING SIGNALK SERVER CONNECTION")
    print("=" * 70)

    data = get_signalk_data()
    if data:
        print("✓ SignalK server is accessible")
        print(f"  Vessel: {data.get('name', 'Unknown')}")
        print(f"  Wind: {data.get('environment', {}).get('wind', {}).get('speedTrue', {}).get('value', 'N/A')} m/s")
        return True
    else:
        print("✗ SignalK server is NOT accessible")
        print("  Check that server is running on http://localhost:80")
        return False

def test_anchor_physics():
    """Test anchor physics and boat behavior"""
    print("\n" + "=" * 70)
    print("ANALYZING BOAT PHYSICS")
    print("=" * 70)

    # Send drop command to chain controller
    print("\nSending drop command to chain controller...")
    if send_signalk_command("navigation.anchor.command", "drop"):
        print("✓ Drop command sent")
    else:
        print("✗ Failed to send drop command")

    # Wait for chain to start deploying
    time.sleep(3)

    # Collect data samples over time
    samples = []
    print("\nCollecting physics data for 30 seconds...")

    for i in range(30):
        data = get_signalk_data()
        if not data:
            print(f"  {i}s: Error getting data")
            time.sleep(1)
            continue

        nav = data.get('navigation', {})
        env = data.get('environment', {})

        sample = {
            'timestamp': datetime.now().isoformat(),
            'time_sec': i,
            'position': nav.get('position', {}).get('value', {}),
            'heading': nav.get('headingTrue', {}).get('value', 0),
            'anchor_pos': nav.get('anchor', {}).get('position', {}).get('value', {}),
            'distance': nav.get('anchor', {}).get('distanceFromBow', {}).get('value', 0),
            'rode_deployed': nav.get('anchor', {}).get('rodeDeployed', {}).get('value', 0),
            'chain_slack': nav.get('anchor', {}).get('chainSlack', {}).get('value', 0),
            'wind_speed': env.get('wind', {}).get('speedTrue', {}).get('value', 0),
            'wind_dir': env.get('wind', {}).get('directionTrue', {}).get('value', 0),
            'depth': env.get('depth', {}).get('belowSurface', {}).get('value', 0),
        }
        samples.append(sample)

        # Print current status
        pos = sample['position']
        anchor_pos = sample['anchor_pos']
        heading_deg = (sample['heading'] * 180 / 3.14159) % 360
        wind_speed = sample['wind_speed']

        # Handle None or invalid position
        try:
            if pos is None or not isinstance(pos, dict) or pos.get('latitude') is None or pos.get('longitude') is None:
                print(f"  {i}s: Position data is invalid - simulation may have crashed")
                continue

            lat = float(pos['latitude']) if pos['latitude'] is not None else None
            lon = float(pos['longitude']) if pos['longitude'] is not None else None

            if lat is None or lon is None:
                print(f"  {i}s: Position data is invalid - simulation may have crashed")
                continue

            print(f"  {i}s: Pos({lat:.6f}, {lon:.6f}) "
                  f"Heading={heading_deg:.0f}° Distance={sample['distance']:.1f}m "
                  f"Rode={sample['rode_deployed']:.1f}m Wind={wind_speed:.1f}m/s "
                  f"Slack={sample['chain_slack']:.1f}m")
        except (TypeError, ValueError, KeyError) as e:
            print(f"  {i}s: Error processing position data: {e}")
            continue

        time.sleep(1)

    if not samples:
        print("✗ No data collected")
        return False

    # Analyze the data
    print("\n" + "-" * 70)
    print("ANALYSIS RESULTS")
    print("-" * 70)

    # Calculate metrics
    distances = [s['distance'] for s in samples]
    headings = [s['heading'] for s in samples]
    rodes = [s['rode_deployed'] for s in samples]
    slacks = [s['chain_slack'] for s in samples]
    wind_speeds = [s['wind_speed'] for s in samples]

    if len(distances) > 1:
        dist_change = distances[-1] - distances[0]
        time_elapsed = samples[-1]['time_sec'] - samples[0]['time_sec']
        drift_rate = dist_change / time_elapsed if time_elapsed > 0 else 0
        print(f"\nDrift Metrics:")
        print(f"  Initial distance: {distances[0]:.1f}m")
        print(f"  Final distance: {distances[-1]:.1f}m")
        print(f"  Change: {dist_change:+.1f}m")
        print(f"  Drift rate: {drift_rate:.3f} m/s")
        if -1.0 <= drift_rate <= 1.0:
            print(f"  ✓ Drift rate in expected range (-1.0 to 1.0 m/s)")
        else:
            print(f"  ✗ Drift rate out of range (expected -1.0 to 1.0 m/s)")

    print(f"\nHeading Metrics:")
    avg_heading = sum(headings) / len(headings) if headings else 0
    avg_heading_deg = (avg_heading * 180 / 3.14159) % 360
    avg_wind_speed = sum(wind_speeds) / len(wind_speeds) if wind_speeds else 0
    print(f"  Average heading: {avg_heading_deg:.1f}°")
    print(f"  Average wind speed: {avg_wind_speed:.2f} m/s")

    print(f"\nRode Metrics:")
    print(f"  Min rode: {min(rodes):.1f}m")
    print(f"  Max rode: {max(rodes):.1f}m")
    print(f"  Rode range: {max(rodes) - min(rodes):.1f}m")

    print(f"\nChain Slack Metrics:")
    print(f"  Min slack: {min(slacks):.1f}m")
    print(f"  Max slack: {max(slacks):.1f}m")
    print(f"  Negative slack count: {sum(1 for s in slacks if s < 0)}")
    if any(s < 0 for s in slacks):
        print(f"  ✗ Chain went slack (negative values detected)")
    else:
        print(f"  ✓ Chain never went slack")

    # Save data
    with open('physics_test_data.json', 'w') as f:
        json.dump(samples, f, indent=2)
    print(f"\n✓ Data saved to physics_test_data.json")

    return True

def main():
    """Main test entry point"""
    print("\n" + "=" * 70)
    print("SIGNALK ANCHOR ALARM PHYSICS TEST")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")

    # Test connection
    if not test_server_connection():
        return False

    # Authenticate for sending commands
    print("\n" + "=" * 70)
    print("AUTHENTICATING")
    print("=" * 70)
    if not get_auth_token():
        print("Warning: Could not authenticate, drop command will fail")

    # Run physics test
    test_anchor_physics()

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    return True

if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)

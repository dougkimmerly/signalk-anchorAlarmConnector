#!/usr/bin/env python3
"""
SignalK Anchor Alarm Test Harness

Connects to a running SignalK server with the anchor alarm connector plugin
and runs predefined test scenarios to validate boat physics simulation.
"""

import json
import time
import requests
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SignalKTestHarness:
    """Manages test execution against a SignalK server"""

    def __init__(self, server_url: str = "http://localhost:80",
                 plugin_base: str = "/plugins/anchoralarm"):
        """
        Initialize the test harness

        Args:
            server_url: Base URL of the SignalK server
            plugin_base: Plugin endpoint base path (anchoralarm plugin)
        """
        self.server_url = server_url.rstrip('/')
        self.plugin_base = plugin_base.rstrip('/')
        self.test_results = []
        self.current_test_data = []

    def is_server_ready(self) -> bool:
        """Check if the SignalK server is running and accessible"""
        try:
            response = requests.get(f"{self.server_url}/api/v1/", timeout=2)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def enable_test_mode(self) -> bool:
        """Enable test mode on the plugin (requires plugin restart)"""
        logger.info("Note: Test mode must be enabled in plugin settings")
        logger.info("Set testMode=true in plugin configuration and restart")
        return True

    def get_anchor_status(self) -> Dict:
        """Retrieve current anchor status from SignalK"""
        try:
            response = requests.get(
                f"{self.server_url}/api/v1/vessels/self/navigation/anchor",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get anchor status: {response.status_code}")
                return {}
        except requests.RequestException as e:
            logger.error(f"Error getting anchor status: {e}")
            return {}

    def drop_anchor(self) -> bool:
        """Simulate dropping the anchor"""
        try:
            response = requests.post(
                f"{self.server_url}{self.plugin_base}/dropAnchor",
                timeout=5
            )
            logger.info(f"Drop anchor response: {response.text}")
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Error dropping anchor: {e}")
            return False

    def raise_anchor(self) -> bool:
        """Simulate raising the anchor"""
        try:
            response = requests.post(
                f"{self.server_url}{self.plugin_base}/raiseAnchor",
                timeout=5
            )
            logger.info(f"Raise anchor response: {response.text}")
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Error raising anchor: {e}")
            return False

    def motor_forward(self) -> bool:
        """Start motor moving forward toward anchor"""
        try:
            response = requests.put(
                f"{self.server_url}{self.plugin_base}/motorforward",
                timeout=5
            )
            logger.info(f"Motor forward response: {response.text}")
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Error starting motor forward: {e}")
            return False

    def motor_backward(self) -> bool:
        """Start motor moving backward away from anchor"""
        try:
            response = requests.put(
                f"{self.server_url}{self.plugin_base}/motorbackward",
                timeout=5
            )
            logger.info(f"Motor backward response: {response.text}")
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Error starting motor backward: {e}")
            return False

    def motor_stop(self) -> bool:
        """Stop the motor"""
        try:
            response = requests.put(
                f"{self.server_url}{self.plugin_base}/motorstop",
                timeout=5
            )
            logger.info(f"Motor stop response: {response.text}")
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Error stopping motor: {e}")
            return False

    def move_to_zone(self, zone: str) -> bool:
        """Move boat to warning or alarm zone"""
        try:
            endpoint = f"movetowarning" if zone.lower() == "warn" else "movetoalarm"
            response = requests.put(
                f"{self.server_url}{self.plugin_base}/{endpoint}",
                timeout=5
            )
            logger.info(f"Move to {zone} response: {response.text}")
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Error moving to zone: {e}")
            return False

    def wait_for_condition(self, condition_fn, timeout: int = 60,
                          check_interval: float = 0.5) -> bool:
        """
        Wait for a condition to become true

        Args:
            condition_fn: Function that returns True when condition is met
            timeout: Maximum time to wait in seconds
            check_interval: How often to check the condition

        Returns:
            True if condition was met, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition_fn():
                return True
            time.sleep(check_interval)
        return False

    def get_test_data(self) -> List[Dict]:
        """Retrieve logged test data from the simulation"""
        # This would need to be exposed by the testSimulation.js module
        # For now, we'll return an empty list and collect data through polling
        return self.current_test_data

    def save_test_results(self, filename: str):
        """Save test results to a JSON file"""
        timestamp = datetime.now().isoformat()
        results = {
            'timestamp': timestamp,
            'server': self.server_url,
            'tests': self.test_results,
            'data_points': len(self.current_test_data)
        }

        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Test results saved to {filename}")
            return True
        except IOError as e:
            logger.error(f"Error saving test results: {e}")
            return False

    def run_test(self, test_name: str, test_fn, duration: int = 30) -> Dict:
        """
        Run a single test and record results

        Args:
            test_name: Name of the test
            test_fn: Function that executes the test
            duration: How long to run the test for (seconds)

        Returns:
            Dictionary with test results
        """
        logger.info(f"Starting test: {test_name}")
        start_time = time.time()

        result = {
            'name': test_name,
            'start_time': datetime.now().isoformat(),
            'duration': duration,
            'success': False,
            'error': None,
            'data_points': 0
        }

        try:
            # Clear previous test data
            self.current_test_data = []

            # Execute the test
            test_fn()

            # Wait for the test to complete
            time.sleep(duration)

            result['success'] = True
            result['data_points'] = len(self.current_test_data)
            logger.info(f"Test {test_name} completed successfully")

        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Test {test_name} failed: {e}")
        finally:
            result['end_time'] = datetime.now().isoformat()
            result['elapsed'] = time.time() - start_time
            self.test_results.append(result)

        return result


def main():
    """Main test harness entry point"""
    logger.info("SignalK Anchor Alarm Test Harness")
    logger.info("=" * 50)

    # Initialize test harness
    harness = SignalKTestHarness()

    # Check server connectivity
    logger.info(f"Connecting to SignalK server at {harness.server_url}...")
    if not harness.is_server_ready():
        logger.error("ERROR: SignalK server is not accessible!")
        logger.info("Please ensure:")
        logger.info("1. SignalK server is running")
        logger.info("2. Anchor Alarm Connector plugin is loaded")
        logger.info("3. Test mode is enabled in plugin settings")
        sys.exit(1)

    logger.info("✓ SignalK server is accessible")

    # Check anchor status
    anchor_status = harness.get_anchor_status()
    if anchor_status:
        logger.info(f"✓ Anchor plugin is responding")
        logger.info(f"  Current anchor position: {anchor_status.get('position', 'Not set')}")
    else:
        logger.warning("! Could not get anchor status - plugin may not be fully initialized")

    logger.info("\nTest harness is ready!")
    logger.info("Use the Python API to run tests:")
    logger.info("  from test_harness import SignalKTestHarness")
    logger.info("  harness = SignalKTestHarness()")
    logger.info("  harness.motor_forward()  # Start motor")
    logger.info("  harness.motor_stop()     # Stop motor")


if __name__ == '__main__':
    main()

#!/bin/bash
#
# START TESTS WITH MANDATORY RESET
# This script enforces proper shutdown/reset before starting tests
#

set -e

echo "======================================"
echo "TEST STARTUP PROCEDURE"
echo "======================================"
echo ""

RESET_SCRIPT="/home/doug/src/signalk-anchorAlarmConnector/validation/scripts/complete_test_reset.sh"
STATUS_SCRIPT="/home/doug/src/signalk-anchorAlarmConnector/validation/scripts/check_test_status.sh"
TEST_RUNNER="/home/doug/src/signalk-anchorAlarmConnector/validation/scripts/overnight_test_runner.py"

# Step 1: Run complete reset
echo "Running complete system reset..."
echo ""
if ! bash "$RESET_SCRIPT"; then
    echo ""
    echo "✗ RESET FAILED - Cannot start tests"
    echo "Please fix the issues above and try again"
    exit 1
fi
echo ""

# Step 2: Verify clean state
echo "Verifying clean state..."
bash "$STATUS_SCRIPT"
echo ""

# Step 3: Final confirmation
echo "About to start test runner..."
echo "Test runner: $TEST_RUNNER"
echo ""
read -p "Continue? (yes/no): " -r RESPONSE
if [[ ! "$RESPONSE" =~ ^[Yy]([Ee][Ss])?$ ]]; then
    echo "Aborted"
    exit 0
fi
echo ""

# Step 4: Start the test runner in background
echo "Starting test runner in background..."
cd /home/doug/src/signalk-anchorAlarmConnector/validation/scripts
nohup python3 overnight_test_runner.py > /tmp/overnight_test_runner.log 2>&1 &
TEST_PID=$!
echo "✓ Test runner started (PID: $TEST_PID)"
echo ""

# Step 5: Monitor for 10 seconds to catch immediate errors
echo "Monitoring initial execution for 10 seconds..."
sleep 10
if ! kill -0 $TEST_PID 2>/dev/null; then
    echo "✗ ERROR: Test runner crashed!"
    echo "Output:"
    tail -20 /tmp/overnight_test_runner.log
    exit 1
fi
echo "✓ Test runner is still running"
echo ""

# Step 6: Show status
echo "======================================"
echo "✓ TESTS STARTED SUCCESSFULLY"
echo "======================================"
echo ""
echo "Test runner PID: $TEST_PID"
echo "Log file: /tmp/overnight_test_runner.log"
echo "Status file: /home/doug/src/signalk-anchorAlarmConnector/validation/data/overnight_tests_*/PROGRESS.txt"
echo ""
echo "To check status: bash $STATUS_SCRIPT"
echo "To view log: tail -f /tmp/overnight_test_runner.log"

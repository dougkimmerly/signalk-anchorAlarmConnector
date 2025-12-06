#!/bin/bash
#
# COMPLETE TEST RESET PROCEDURE
# This script performs a comprehensive shutdown and reset of the entire test environment
# RUN THIS BEFORE EVERY NEW TEST SESSION
#

set -e

echo "======================================"
echo "COMPLETE TEST RESET PROCEDURE"
echo "======================================"
echo ""

# STEP 1: Verify token
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkZXZpY2UiOiI5MWEzNjE2Yi04MTQyLTQ2ZjUtODM2Zi1hMDNhNmY5MmU3YjQiLCJpYXQiOjE3NjEwMDE2Nzh9.boMHMK8KAqbMrV933rMozjTDHpEH8sIDUv1EKd8_KcE"

# STEP 2: Kill all Python test processes
echo "Step 1: Killing all Python test processes..."
pkill -9 -f "overnight_test_runner" 2>/dev/null || true
pkill -9 -f "phase.*test" 2>/dev/null || true
sleep 2

# Verify all processes are dead
REMAINING=$(ps aux | grep -iE "overnight_test_runner|python3.*test" | grep -v grep | wc -l)
if [ "$REMAINING" -gt 0 ]; then
    echo "✗ ERROR: Test processes still running! ($REMAINING processes)"
    ps aux | grep -iE "overnight_test_runner|python3.*test" | grep -v grep
    exit 1
fi
echo "✓ All test processes killed"
echo ""

# STEP 3: Send STOP command to anchor chain controller
echo "Step 2: Stopping anchor chain controller..."
curl -s -X PUT http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/command \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": "stop"}' > /dev/null 2>&1 || true
sleep 1
echo "✓ Stop command sent to chain controller"
echo ""

# STEP 4: Reset rode to 0m (between stop command and chain stop)
echo "Step 3: Resetting anchor rode to 0m..."
curl -s -X PUT http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/rodeDeployed \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": 1}' > /dev/null 2>&1 || true
sleep 1

# Verify reset
RODE_AFTER=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/rodeDeployed 2>/dev/null | python3 -c "import json, sys; d=json.load(sys.stdin); print(d.get('value', 0))" 2>/dev/null || echo "999")
echo "Rode after reset: ${RODE_AFTER}m"

if (( $(echo "$RODE_AFTER > 0.5" | bc -l) )); then
    echo "✗ ERROR: Rode did not reset properly!"
    exit 1
fi
echo "✓ Anchor rode reset successful"
echo ""

# STEP 5: Wait before restarting SignalK (allow chain to fully stop)
echo "Step 4: Waiting for chain controller to stop completely..."
sleep 2
echo "✓ Chain stop confirmed"
echo ""

# STEP 7: Restart SignalK
echo "Step 6: Restarting SignalK server..."
sudo systemctl restart signalk
sleep 4
echo "✓ SignalK restarted"
echo ""

# STEP 7: Verify SignalK is responding
echo "Step 6: Verifying SignalK server..."
if ! curl -s http://localhost:80/signalk > /dev/null 2>&1; then
    echo "✗ ERROR: SignalK not responding!"
    exit 1
fi
echo "✓ SignalK is responding"
echo ""

# STEP 8: Verify simulation is active
echo "Step 7: Verifying V2 simulation..."
if ! curl -s http://localhost:80/plugins/signalk-anchoralarmconnector/simulation/state > /dev/null 2>&1; then
    echo "✗ ERROR: Simulation not responding!"
    exit 1
fi
echo "✓ V2 simulation is active"
echo ""

# STEP 9: Check final anchor state
echo "Step 8: Verifying final anchor state..."
FINAL_RODE=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/rodeDeployed 2>/dev/null | python3 -c "import json, sys; d=json.load(sys.stdin); print(d.get('value', 0))" 2>/dev/null || echo "999")
FINAL_CMD=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/command 2>/dev/null | python3 -c "import json, sys; d=json.load(sys.stdin); print(d.get('value', 'unknown'))" 2>/dev/null || echo "unknown")
echo "Final rode: ${FINAL_RODE}m"
echo "Final command: ${FINAL_CMD}"

if (( $(echo "$FINAL_RODE > 0.5" | bc -l) )); then
    echo "✗ ERROR: Final rode is still deployed!"
    exit 1
fi
echo "✓ Anchor is clean (0m rode, stop command)"
echo ""

# STEP 10: Clean old test directories
echo "Step 9: Cleaning old test directories..."
rm -rf /home/doug/src/signalk-anchorAlarmConnector/validation/data/overnight_tests_* 2>/dev/null || true
rm -rf /home/doug/src/test_framework/overnight_tests_* 2>/dev/null || true
echo "✓ Old test directories cleaned"
echo ""

echo "======================================"
echo "✓ COMPLETE RESET SUCCESSFUL"
echo "======================================"
echo ""
echo "System is ready for new test session"
echo "You can now run: python3 overnight_test_runner.py"

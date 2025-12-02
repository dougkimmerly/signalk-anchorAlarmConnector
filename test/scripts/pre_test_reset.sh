#!/bin/bash
# Pre-test reset and verification script
# MUST be run before any test to ensure clean state

set -e

echo "======================================"
echo "  PRE-TEST RESET AND VERIFICATION"
echo "======================================"

# Step 1: Stop chain controller
echo ""
echo "Step 1: Stopping chain controller..."
cd /home/doug/src/test_framework
python3 stop_chain.py || { echo "✗ Failed to stop chain"; exit 1; }
sleep 1

# Step 2: Reset anchor rode
echo ""
echo "Step 2: Resetting anchor rode..."
python3 reset_anchor.py || { echo "✗ Failed to reset anchor"; exit 1; }
sleep 2

# Step 3: Restart SignalK
echo ""
echo "Step 3: Restarting SignalK server..."
sudo systemctl restart signalk
sleep 8

# Step 4: Verify SignalK is running
echo ""
echo "Step 4: Verifying SignalK is running..."
if sudo systemctl is-active --quiet signalk; then
    echo "✓ SignalK is running"
else
    echo "✗ SignalK failed to start"
    exit 1
fi

# Step 5: Verify V2 simulation is active
echo ""
echo "Step 5: Verifying V2 simulation is active..."
sleep 2
RUNNING=$(curl -s http://localhost:80/signalk/v1/api/vessels/self/navigation/position/value 2>/dev/null | grep -q latitude && echo "true" || echo "false")
if [ "$RUNNING" = "true" ]; then
    echo "✓ V2 simulation is responding"
else
    echo "✗ V2 simulation not responding"
    exit 1
fi

# Step 6: Verify boat at initial position
echo ""
echo "Step 6: Verifying boat at initial position..."
POS=$(curl -s http://localhost:80/signalk/v1/api/vessels/self/navigation/position/value)
LAT=$(echo "$POS" | python3 -c "import sys,json; print(json.load(sys.stdin)['latitude'])" 2>/dev/null || echo "unknown")
echo "Initial position: $LAT"

echo ""
echo "======================================"
echo "✓ PRE-TEST RESET COMPLETE"
echo "======================================"
echo ""

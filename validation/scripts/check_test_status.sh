#!/bin/bash
#
# CHECK TEST STATUS
# Shows current status of test runner and system
#

TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkZXZpY2UiOiI5MWEzNjE2Yi04MTQyLTQ2ZjUtODM2Zi1hMDNhNmY5MmU3YjQiLCJpYXQiOjE3NjEwMDE2Nzh9.boMHMK8KAqbMrV933rMozjTDHpEH8sIDUv1EKd8_KcE"

echo "======================================"
echo "TEST STATUS CHECK"
echo "======================================"
echo ""

# Check 1: Are test processes running?
echo "1. Test Process Status:"
TEST_COUNT=$(ps aux | grep -iE "overnight_test_runner|python3.*test" | grep -v grep | wc -l)
if [ "$TEST_COUNT" -gt 0 ]; then
    echo "   ✓ Test runner is RUNNING ($TEST_COUNT processes)"
    ps aux | grep -iE "overnight_test_runner|python3.*test" | grep -v grep | awk '{print "     PID:", $2, "CMD:", $NF}'
else
    echo "   ✗ No test processes running"
fi
echo ""

# Check 2: SignalK Server
echo "2. SignalK Server Status:"
if curl -s http://localhost:80/signalk > /dev/null 2>&1; then
    echo "   ✓ SignalK server is RUNNING"
else
    echo "   ✗ SignalK server is NOT RESPONDING"
fi
echo ""

# Check 3: Simulation
echo "3. Simulation Status:"
if curl -s http://localhost:80/plugins/signalk-anchoralarmconnector/simulation/state > /dev/null 2>&1; then
    echo "   ✓ V2 Simulation is ACTIVE"
else
    echo "   ✗ V2 Simulation is NOT RESPONDING"
fi
echo ""

# Check 4: Anchor State
echo "4. Anchor State:"
RODE=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/rodeDeployed 2>/dev/null | python3 -c "import json, sys; d=json.load(sys.stdin); print(d.get('value', 'ERROR'))" 2>/dev/null || echo "ERROR")
CMD=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:80/signalk/v1/api/vessels/self/navigation/anchor/command 2>/dev/null | python3 -c "import json, sys; d=json.load(sys.stdin); print(d.get('value', 'ERROR'))" 2>/dev/null || echo "ERROR")
echo "   Rode Deployed: ${RODE}m"
echo "   Command State: ${CMD}"
echo ""

# Check 5: Current Test Progress
echo "5. Test Progress:"
if [ -f /home/doug/src/signalk-anchorAlarmConnector/validation/data/overnight_tests_*/PROGRESS.txt ]; then
    cat /home/doug/src/signalk-anchorAlarmConnector/validation/data/overnight_tests_*/PROGRESS.txt 2>/dev/null | while IFS= read -r line; do
        echo "   $line"
    done
else
    echo "   (No active test session)"
fi
echo ""

# Check 6: Test Directory Size
echo "6. Data Collection:"
TEST_COUNT=$(find /home/doug/src/signalk-anchorAlarmConnector/validation/data/overnight_tests_* -name "*.json" 2>/dev/null | wc -l)
if [ "$TEST_COUNT" -gt 0 ]; then
    echo "   Data files collected: $TEST_COUNT"
    SIZE=$(du -sh /home/doug/src/signalk-anchorAlarmConnector/validation/data/overnight_tests_* 2>/dev/null | awk '{print $1}')
    echo "   Total size: $SIZE"
else
    echo "   (No data collected yet)"
fi
echo ""

echo "======================================"

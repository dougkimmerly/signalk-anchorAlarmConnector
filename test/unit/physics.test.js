#!/usr/bin/env node
/**
 * Physics Module Test Script
 *
 * Tests the physics modules in isolation without SignalK.
 * Run with: node test/unit/physics.test.js
 */

const { createBoat, createEnvironment, createIntegrator, config } = require('../../plugin/physics')

// Disable verbose logging for tests
config.config.logging.logInterval = 1000  // Only log every 1000 iterations

console.log('===========================================')
console.log('   PHYSICS MODULE TESTS')
console.log('===========================================\n')

let testsRun = 0
let testsPassed = 0

function test(name, fn) {
  testsRun++
  try {
    fn()
    console.log(`✓ ${name}`)
    testsPassed++
  } catch (error) {
    console.log(`✗ ${name}`)
    console.log(`  Error: ${error.message}`)
  }
}

function assertApprox(actual, expected, tolerance, message) {
  if (Math.abs(actual - expected) > tolerance) {
    throw new Error(`${message}: expected ${expected} ± ${tolerance}, got ${actual}`)
  }
}

function assertTrue(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

// ============================================
// TEST 1: Wind force direction
// ============================================
console.log('\n--- Wind Force Direction Tests ---')

test('Wind from South (180°) pushes North (+Y)', () => {
  const { calculateWindForce } = require('../../plugin/physics/forces/wind')
  const force = calculateWindForce(10, 180, 0)

  // Wind from South should push North (positive Y)
  assertTrue(force.forceY > 0, `Expected positive Y force, got ${force.forceY}`)
  assertApprox(force.forceX, 0, 10, 'X force should be ~0')
  assertApprox(force.pushDirection, 0, 0.1, 'Push direction should be 0° (North)')
})

test('Wind from North (0°) pushes South (-Y)', () => {
  const { calculateWindForce } = require('../../plugin/physics/forces/wind')
  const force = calculateWindForce(10, 0, 0)

  assertTrue(force.forceY < 0, `Expected negative Y force, got ${force.forceY}`)
  assertApprox(force.forceX, 0, 10, 'X force should be ~0')
})

test('Wind from East (90°) pushes West (-X)', () => {
  const { calculateWindForce } = require('../../plugin/physics/forces/wind')
  const force = calculateWindForce(10, 90, 0)

  assertTrue(force.forceX < 0, `Expected negative X force, got ${force.forceX}`)
  assertApprox(force.forceY, 0, 10, 'Y force should be ~0')
})

test('Wind from West (270°) pushes East (+X)', () => {
  const { calculateWindForce } = require('../../plugin/physics/forces/wind')
  const force = calculateWindForce(10, 270, 0)

  assertTrue(force.forceX > 0, `Expected positive X force, got ${force.forceX}`)
  assertApprox(force.forceY, 0, 10, 'Y force should be ~0')
})

// ============================================
// TEST 2: Wind force magnitude
// ============================================
console.log('\n--- Wind Force Magnitude Tests ---')

test('Wind force increases with speed squared', () => {
  const { calculateWindForce } = require('../../plugin/physics/forces/wind')
  const force10 = calculateWindForce(10, 180, 0)
  const force20 = calculateWindForce(20, 180, 0)

  // 20 knots should produce 4x the force of 10 knots (squared)
  const ratio = force20.forceMagnitude / force10.forceMagnitude
  assertApprox(ratio, 4, 0.1, 'Force should scale with speed squared')
})

test('10 knot wind produces reasonable force (~475N)', () => {
  const { calculateWindForce } = require('../../plugin/physics/forces/wind')
  const force = calculateWindForce(10, 180, 0)

  // F = 0.5 * 1.2 * 30 * 1.0 * (10 * 0.51444)² ≈ 476 N
  assertApprox(force.forceMagnitude, 476, 50, 'Force magnitude')
})

// ============================================
// TEST 3: Water drag
// ============================================
console.log('\n--- Water Drag Tests ---')

test('Drag opposes velocity direction', () => {
  const { calculateWaterDrag } = require('../../plugin/physics/forces/waterDrag')

  // Moving East (+X), heading East (90°) - forward motion
  const drag = calculateWaterDrag(1, 0, 90)
  assertTrue(drag.forceX < 0, 'Drag should oppose X velocity')
  assertApprox(drag.forceY, 0, 0.1, 'Y drag should be 0 for X-only velocity')
})

test('Drag increases with velocity squared', () => {
  const { calculateWaterDrag } = require('../../plugin/physics/forces/waterDrag')

  // Same heading for both to ensure same coefficient
  const drag1 = calculateWaterDrag(1, 0, 90)
  const drag2 = calculateWaterDrag(2, 0, 90)

  const ratio = Math.abs(drag2.forceX) / Math.abs(drag1.forceX)
  assertApprox(ratio, 4, 0.1, 'Drag should scale with velocity squared')
})

test('Directional drag: forward has lowest coefficient', () => {
  const { calculateWaterDrag } = require('../../plugin/physics/forces/waterDrag')

  // Moving North, heading North (0°) - forward motion
  const forward = calculateWaterDrag(0, 1, 0)

  // Moving North, heading South (180°) - backward motion
  const backward = calculateWaterDrag(0, 1, 180)

  // Moving North, heading East (90°) - sideways motion
  const sideways = calculateWaterDrag(0, 1, 90)

  // Forward should have least drag, sideways most
  assertTrue(Math.abs(forward.forceY) < Math.abs(backward.forceY),
    `Forward drag (${Math.abs(forward.forceY).toFixed(1)}) should be less than backward (${Math.abs(backward.forceY).toFixed(1)})`)
  assertTrue(Math.abs(backward.forceY) < Math.abs(sideways.forceY),
    `Backward drag (${Math.abs(backward.forceY).toFixed(1)}) should be less than sideways (${Math.abs(sideways.forceY).toFixed(1)})`)
})

// ============================================
// TEST 4: Terminal velocity calculation
// ============================================
console.log('\n--- Terminal Velocity Tests ---')

test('Terminal velocity calculation is correct', () => {
  const { calculateTerminalVelocity } = require('../../plugin/physics/forces/waterDrag')

  // With 400N force and forwardCoeff 28: v_term = sqrt(400/28) = 3.78 m/s
  const vTerm = calculateTerminalVelocity(400)
  assertApprox(vTerm, 3.78, 0.1, 'Terminal velocity (forward)')
})

test('Directional terminal velocities match target speeds', () => {
  const { calculateDirectionalTerminalVelocities } = require('../../plugin/physics/forces/waterDrag')

  // Wind force at 10kn ≈ 476N
  const vTerms = calculateDirectionalTerminalVelocities(476)

  // Forward: ~8kn = ~4.1 m/s
  assertApprox(vTerms.forward, 4.1, 0.2, 'Forward terminal velocity')

  // Backward: ~4kn = ~2.1 m/s
  assertApprox(vTerms.backward, 2.1, 0.2, 'Backward terminal velocity')

  // Sideways: ~2kn = ~1.0 m/s
  assertApprox(vTerms.sideways, 1.0, 0.2, 'Sideways terminal velocity')
})

// ============================================
// TEST 5: Boat movement integration
// ============================================
console.log('\n--- Boat Integration Tests ---')

test('Boat moves North with South wind (10 iterations)', () => {
  const boat = createBoat({ latitude: 0, longitude: 0, heading: 180 })
  const env = createEnvironment({ windSpeed: 20, windDirection: 180 })
  const integrator = createIntegrator(boat, env)

  const initialLat = boat.getState().latitude

  // Run 10 physics steps
  for (let i = 0; i < 10; i++) {
    integrator.step()
  }

  const finalLat = boat.getState().latitude
  assertTrue(finalLat > initialLat, `Boat should move North: ${initialLat} -> ${finalLat}`)
})

test('Boat reaches terminal velocity (100 iterations)', () => {
  const boat = createBoat({ latitude: 0, longitude: 0 })
  const env = createEnvironment({ windSpeed: 10, windDirection: 180 })
  const integrator = createIntegrator(boat, env)

  // Run 100 physics steps (5 seconds at 20Hz)
  for (let i = 0; i < 100; i++) {
    integrator.step()
  }

  const state = boat.getState()
  const speed = state.speed

  // Should approach terminal velocity
  // Wind force ~476N, terminal velocity = sqrt(476/20) ≈ 4.9 m/s
  // But 5 seconds isn't enough to reach it, should be accelerating toward it
  assertTrue(speed > 0.1, `Boat should be moving: ${speed} m/s`)
  assertTrue(speed < 10, `Speed should be reasonable: ${speed} m/s`)
})

test('Boat slows down with no wind (drag only)', () => {
  // Disable wind for this test
  config.setForceEnabled('wind', false)

  const boat = createBoat({ latitude: 0, longitude: 0, velocityY: 2 })
  const env = createEnvironment({ windSpeed: 0, windDirection: 180 })
  const integrator = createIntegrator(boat, env)

  const initialSpeed = boat.getState().speed

  // Run 50 physics steps
  for (let i = 0; i < 50; i++) {
    integrator.step()
  }

  const finalSpeed = boat.getState().speed

  // Re-enable wind
  config.setForceEnabled('wind', true)

  assertTrue(finalSpeed < initialSpeed, `Boat should slow: ${initialSpeed} -> ${finalSpeed}`)
})

// ============================================
// TEST 6: Heading behavior (weathervane - free boat)
// ============================================
console.log('\n--- Heading Tests (Free Boat) ---')

test('Free boat heading rotates toward wind source', () => {
  // Start pointing East (90°), wind from South (180°)
  const boat = createBoat({ latitude: 0, longitude: 0, heading: 90 })
  const env = createEnvironment({ windSpeed: 15, windDirection: 180 })
  const integrator = createIntegrator(boat, env)

  const initialHeading = boat.getState().heading

  // Run 200 physics steps (10 seconds)
  for (let i = 0; i < 200; i++) {
    integrator.step()
  }

  const finalHeading = boat.getState().heading

  // Heading should move toward 180° (wind source)
  const initialDiff = Math.abs(180 - initialHeading)
  const finalDiff = Math.abs(180 - finalHeading)

  assertTrue(finalDiff < initialDiff, `Heading should approach wind: ${initialHeading}° -> ${finalHeading}°`)
})

// ============================================
// TEST 7: Anchored heading behavior
// ============================================
console.log('\n--- Heading Tests (Anchored Boat) ---')

test('Anchored boat heading rotates toward anchor', () => {
  // Boat at origin, anchor to the North (0°)
  const boat = createBoat({ latitude: 0, longitude: 0, heading: 90 })
  const env = createEnvironment({ windSpeed: 10, windDirection: 90 })  // Wind from East
  const integrator = createIntegrator(boat, env)

  // Set anchor to the North (bearing 0° from boat)
  boat.setAnchor(0.0001, 0)  // North of current position

  const initialHeading = boat.getState().heading

  // Run 200 physics steps (10 seconds)
  for (let i = 0; i < 200; i++) {
    integrator.step({ rodeDeployed: 20 })
  }

  const finalHeading = boat.getState().heading

  // Heading should move primarily toward anchor (0°), not wind source (90°)
  // Since anchor dominates, we expect heading closer to 0° than to 90°
  const initialDiffToAnchor = Math.abs(normalizeAngle(0 - initialHeading))
  const finalDiffToAnchor = Math.abs(normalizeAngle(0 - finalHeading))

  assertTrue(finalDiffToAnchor < initialDiffToAnchor,
    `Anchored heading should approach anchor: ${initialHeading}° -> ${finalHeading}° (target: 0°)`)
})

test('Anchored boat shows wind influence when chain slack', () => {
  // Boat at origin, anchor to the North (0°)
  const boat = createBoat({ latitude: 0, longitude: 0, heading: 180 })  // Pointing South
  const env = createEnvironment({ windSpeed: 20, windDirection: 90 })  // Strong wind from East
  const integrator = createIntegrator(boat, env)

  // Set anchor to the North, lots of slack
  boat.setAnchor(0.00001, 0)  // Very close anchor (lots of slack)

  // Run 600 physics steps (30 seconds) - with higher damping, rotation is slower but smoother
  for (let i = 0; i < 600; i++) {
    integrator.step({ rodeDeployed: 50 })  // 50m rode, very slack
  }

  const finalHeading = boat.getState().heading

  // With lots of slack, wind should have some influence
  // Heading should not be exactly toward anchor (0°)
  // It should be somewhere between anchor direction (0°) and wind source (90°)
  // With higher damping, rotation is smoother but slower - verify at least 3° movement
  assertTrue(Math.abs(normalizeAngle(finalHeading - 180)) > 3,
    `Anchored boat should respond to forces: heading=${finalHeading}°`)
})

test('Combined torque tension factor varies with slack', () => {
  const { calculateAnchoredHeadingTorque } = require('../../plugin/physics/forces/wind')

  // Tight chain (distance close to rode length)
  const tightResult = calculateAnchoredHeadingTorque(0, 90, 45, 15, 18, 20)

  // Slack chain (distance much less than rode length)
  const slackResult = calculateAnchoredHeadingTorque(0, 90, 45, 15, 5, 20)

  // Tight chain should have higher tension factor (anchor dominates more)
  assertTrue(tightResult.tensionFactor > slackResult.tensionFactor,
    `Tight chain should have higher tension factor: tight=${tightResult.tensionFactor.toFixed(2)} vs slack=${slackResult.tensionFactor.toFixed(2)}`)

  // Wind factor should be complementary
  assertApprox(tightResult.tensionFactor + tightResult.windFactor, 1, 0.01, 'Factors should sum to 1')
  assertApprox(slackResult.tensionFactor + slackResult.windFactor, 1, 0.01, 'Factors should sum to 1')
})

// Helper to normalize angle to -180 to +180
function normalizeAngle(angle) {
  while (angle > 180) angle -= 360
  while (angle < -180) angle += 360
  return angle
}

// ============================================
// TEST 8: Slack Constraint (Velocity Constraint / Dead Stop)
// Slack is provided by chain controller via SignalK
// When slack <= buffer (0.5m default), velocity away from anchor is zeroed (dead stop)
// Buffer prevents overshoot - constraint activates slightly before fully taut
// ============================================
console.log('\n--- Slack Constraint Tests (Velocity Constraint) ---')

test('Constraint not active when slack > buffer', () => {
  const { isConstraintActive } = require('../../plugin/physics/forces/slackConstraint')
  // Buffer is 0.5m by default, so slack > 0.5 should not be constrained

  assertTrue(!isConstraintActive(5), 'slack=5 should not be constrained')
  assertTrue(!isConstraintActive(1), 'slack=1 should not be constrained')
  assertTrue(!isConstraintActive(0.6), 'slack=0.6 should not be constrained (> 0.5 buffer)')
})

test('Constraint active when slack <= buffer', () => {
  const { isConstraintActive } = require('../../plugin/physics/forces/slackConstraint')
  // Buffer is 0.5m by default, so slack <= 0.5 should be constrained

  assertTrue(isConstraintActive(0.5), 'slack=0.5 should be constrained (= buffer)')
  assertTrue(isConstraintActive(0.3), 'slack=0.3 should be constrained (< buffer)')
  assertTrue(isConstraintActive(0), 'slack=0 should be constrained')
  assertTrue(isConstraintActive(-1), 'slack=-1 should be constrained')
})

test('Tension ratio calculation', () => {
  const { calculateTensionRatio } = require('../../plugin/physics/forces/slackConstraint')
  const depth = 3

  assertApprox(calculateTensionRatio(5, depth), 0, 0.01, 'slack > depth = 0 tension')
  assertApprox(calculateTensionRatio(3, depth), 0, 0.01, 'slack = depth = 0 tension')
  assertApprox(calculateTensionRatio(1.5, depth), 0.5, 0.01, 'slack = depth/2 = 0.5 tension')
  assertApprox(calculateTensionRatio(0, depth), 1.0, 0.01, 'slack = 0 = 1.0 tension')
  assertTrue(calculateTensionRatio(-1, depth) > 1, 'slack < 0 = tension > 1')
})

test('Chain weight force scales with suspended chain length', () => {
  const { calculateChainWeightForce } = require('../../plugin/physics/forces/slackConstraint')
  const depth = 3
  const bearingToAnchor = 0  // Anchor to North

  // At slack >= depth, no chain suspended, no force
  const noForce = calculateChainWeightForce(depth, depth, bearingToAnchor)
  assertApprox(noForce.magnitude, 0, 0.01, 'slack=depth should have 0 force')
  assertApprox(noForce.suspendedLength, 0, 0.01, 'slack=depth should have 0 suspended')

  // At slack = 0, full depth suspended
  // Force = depth * chainWeightPerMeter * gravity = 3 * 2.5 * 9.81 = 73.6N
  const fullForce = calculateChainWeightForce(0, depth, bearingToAnchor)
  assertApprox(fullForce.suspendedLength, 3, 0.01, 'slack=0 should suspend full depth')
  assertApprox(fullForce.magnitude, 73.6, 1, 'slack=0 force ~73.6N')

  // At slack = 1.5 (half depth), half chain suspended
  const halfForce = calculateChainWeightForce(1.5, depth, bearingToAnchor)
  assertApprox(halfForce.suspendedLength, 1.5, 0.01, 'slack=1.5 should suspend half')
  assertApprox(halfForce.magnitude, 36.8, 1, 'slack=1.5 force ~36.8N')
})

test('Chain weight force direction is toward anchor', () => {
  const { calculateChainWeightForce } = require('../../plugin/physics/forces/slackConstraint')
  const depth = 3
  const slack = 0  // Full force

  // Anchor to North (0°) - force should be +Y
  const northForce = calculateChainWeightForce(slack, depth, 0)
  assertTrue(northForce.forceY > 0, 'Anchor North: forceY should be positive')
  assertApprox(northForce.forceX, 0, 0.1, 'Anchor North: forceX should be ~0')

  // Anchor to East (90°) - force should be +X
  const eastForce = calculateChainWeightForce(slack, depth, 90)
  assertTrue(eastForce.forceX > 0, 'Anchor East: forceX should be positive')
  assertApprox(eastForce.forceY, 0, 0.1, 'Anchor East: forceY should be ~0')

  // Anchor to South (180°) - force should be -Y
  const southForce = calculateChainWeightForce(slack, depth, 180)
  assertTrue(southForce.forceY < 0, 'Anchor South: forceY should be negative')
  assertApprox(southForce.forceX, 0, 0.1, 'Anchor South: forceX should be ~0')
})

test('Velocity constraint zeros movement away from anchor', () => {
  // Create boat moving South (away from anchor to the North)
  const boat = createBoat({ latitude: 0, longitude: 0, heading: 180, velocityX: 0, velocityY: -2 })

  // Set velocity constraint active with anchor to the North (0°)
  boat.setVelocityConstraint(true, 0)

  // Run update - should zero the away component
  boat.update()

  const state = boat.getState()
  // Velocity toward South should be zeroed
  assertTrue(state.velocityY >= 0, `Velocity away from anchor should be zeroed: got ${state.velocityY}`)
})

test('Velocity constraint allows movement toward anchor', () => {
  // Create boat moving North (toward anchor to the North)
  const boat = createBoat({ latitude: 0, longitude: 0, heading: 0, velocityX: 0, velocityY: 2 })

  // Set velocity constraint active with anchor to the North (0°)
  boat.setVelocityConstraint(true, 0)

  // Run update - should keep the toward component
  boat.update()

  const state = boat.getState()
  // Velocity toward North should be preserved (minus any drag etc - but direction should be same)
  assertTrue(state.velocityY >= 0, `Velocity toward anchor should be allowed: got ${state.velocityY}`)
})

test('Velocity constraint allows perpendicular movement', () => {
  // Create boat moving East (perpendicular to anchor to the North)
  const boat = createBoat({ latitude: 0, longitude: 0, heading: 90, velocityX: 2, velocityY: 0 })

  // Set velocity constraint active with anchor to the North (0°)
  boat.setVelocityConstraint(true, 0)

  // Run update - should allow perpendicular movement
  boat.update()

  const state = boat.getState()
  // Velocity East should be preserved
  assertTrue(state.velocityX > 0, `Perpendicular velocity should be allowed: got ${state.velocityX}`)
})

// ============================================
// TEST 9: Motor Force
// ============================================
console.log('\n--- Motor Force Tests ---')

test('Motor stop produces no force', () => {
  const { calculateMotorForce, setMotorDirection, setMotorThrottle } = require('../../plugin/physics/forces/motor')

  setMotorDirection('stop')
  setMotorThrottle(1.0)

  const force = calculateMotorForce(0)
  assertApprox(force.magnitude, 0, 0.01, 'Stop should produce 0 force')
  assertApprox(force.forceX, 0, 0.01, 'forceX should be 0')
  assertApprox(force.forceY, 0, 0.01, 'forceY should be 0')
})

test('Motor forward thrusts along heading', () => {
  const { calculateMotorForce, setMotorDirection, setMotorThrottle } = require('../../plugin/physics/forces/motor')

  setMotorDirection('forward')
  setMotorThrottle(1.0)

  // Heading North (0°) - thrust should be +Y
  const forceNorth = calculateMotorForce(0)
  assertTrue(forceNorth.forceY > 0, 'Heading North: forceY should be positive')
  assertApprox(forceNorth.forceX, 0, 1, 'Heading North: forceX should be ~0')
  assertApprox(forceNorth.magnitude, 500, 1, 'Forward thrust should be 500N')

  // Heading East (90°) - thrust should be +X
  const forceEast = calculateMotorForce(90)
  assertTrue(forceEast.forceX > 0, 'Heading East: forceX should be positive')
  assertApprox(forceEast.forceY, 0, 1, 'Heading East: forceY should be ~0')
})

test('Motor backward thrusts opposite to heading', () => {
  const { calculateMotorForce, setMotorDirection, setMotorThrottle } = require('../../plugin/physics/forces/motor')

  setMotorDirection('backward')
  setMotorThrottle(1.0)

  // Heading North (0°) - backward thrust should be -Y (pushing boat South)
  const forceNorth = calculateMotorForce(0)
  assertTrue(forceNorth.forceY < 0, 'Heading North, backward: forceY should be negative')
  assertApprox(forceNorth.forceX, 0, 1, 'Heading North, backward: forceX should be ~0')
  assertApprox(forceNorth.magnitude, 300, 1, 'Backward thrust should be 300N')

  // Heading East (90°) - backward thrust should be -X
  const forceEast = calculateMotorForce(90)
  assertTrue(forceEast.forceX < 0, 'Heading East, backward: forceX should be negative')
  assertApprox(forceEast.forceY, 0, 1, 'Heading East, backward: forceY should be ~0')
})

test('Motor throttle scales force', () => {
  const { calculateMotorForce, setMotorDirection, setMotorThrottle } = require('../../plugin/physics/forces/motor')

  setMotorDirection('forward')

  setMotorThrottle(1.0)
  const full = calculateMotorForce(0)

  setMotorThrottle(0.5)
  const half = calculateMotorForce(0)

  setMotorThrottle(0.0)
  const zero = calculateMotorForce(0)

  assertApprox(full.magnitude, 500, 1, 'Full throttle = 500N')
  assertApprox(half.magnitude, 250, 1, 'Half throttle = 250N')
  assertApprox(zero.magnitude, 0, 0.01, 'Zero throttle = 0N')

  // Reset motor state
  setMotorDirection('stop')
})

test('Motor state management', () => {
  const { setMotorDirection, setMotorThrottle, getMotorState } = require('../../plugin/physics/forces/motor')

  setMotorDirection('forward')
  setMotorThrottle(0.75)

  const state = getMotorState()
  assertTrue(state.direction === 'forward', `Direction should be forward: ${state.direction}`)
  assertApprox(state.throttle, 0.75, 0.01, 'Throttle should be 0.75')

  // Reset
  setMotorDirection('stop')
  setMotorThrottle(1.0)
})

test('Motor integrates with physics loop', () => {
  // Enable motor force for this test
  config.setForceEnabled('motor', true)

  const { setMotorDirection, setMotorThrottle } = require('../../plugin/physics/forces/motor')

  // Heading South (180°), motor forward = thrust South (-Y)
  const boat = createBoat({ latitude: 0, longitude: 0, heading: 180, velocityX: 0, velocityY: 0 })
  const env = createEnvironment({ windSpeed: 0, windDirection: 0 })  // No wind
  config.setForceEnabled('wind', false)  // Disable wind
  const integrator = createIntegrator(boat, env)

  setMotorDirection('forward')
  setMotorThrottle(1.0)

  const initialLat = boat.getState().latitude

  // Run 20 physics steps (1 second)
  for (let i = 0; i < 20; i++) {
    integrator.step()
  }

  const finalLat = boat.getState().latitude
  const state = boat.getState()

  // Boat should move South (negative latitude)
  assertTrue(finalLat < initialLat, `Boat should move South: ${initialLat} -> ${finalLat}`)
  assertTrue(state.velocityY < 0, `Velocity should be negative (South): ${state.velocityY}`)

  // Cleanup
  setMotorDirection('stop')
  config.setForceEnabled('motor', false)
  config.setForceEnabled('wind', true)
})

// ============================================
// SUMMARY
// ============================================
console.log('\n===========================================')
console.log(`   RESULTS: ${testsPassed}/${testsRun} tests passed`)
console.log('===========================================')

if (testsPassed < testsRun) {
  process.exit(1)
}

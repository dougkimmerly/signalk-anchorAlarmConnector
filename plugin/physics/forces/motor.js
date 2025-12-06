/**
 * Motor Force Module
 *
 * Applies thrust along the boat's heading direction.
 * Used to supplement wind/catenary forces during anchor operations.
 *
 * USE CASES:
 * 1. Deployment (motorBackward): Move boat away from anchor when wind is insufficient
 *    - Applies thrust in reverse (opposite to heading)
 *    - Target speed ~1kn (0.5 m/s) away from anchor
 *
 * 2. Retrieval (motorForward): Move boat toward anchor to create chain slack
 *    - Applies thrust forward (along heading)
 *    - Supplements catenary force to provide slack for chain lifting
 *
 * CONTROL:
 * - Motor state is set by simulator via HTTP endpoints or automatic logic
 * - NOT controlled by chain controller (ESP32)
 */

const { config } = require('../../config/simulationConfig')

/**
 * Motor state - controlled by simulator or manually via PUT handlers
 */
let motorState = {
  direction: 'stop',  // 'forward', 'backward', 'stop'
  throttle: 1.0,      // 0.0 to 1.0 (percentage of max thrust)
  manualMode: false,  // true when user manually controls via PUT handlers
}

/**
 * Track when manual mode was last set to prevent auto-motor from interfering
 */
let manualModeTimeout = null
const MANUAL_MODE_DURATION = 30000  // 30 seconds - keep manual mode active after manual command

/**
 * Enable manual mode to prevent auto-motor from interfering
 * @param {boolean} enabled - true to enable manual mode
 */
function setManualMode(enabled) {
  motorState.manualMode = enabled

  if (enabled) {
    // Clear any existing timeout
    if (manualModeTimeout) {
      clearTimeout(manualModeTimeout)
    }
    // Set timeout to disable manual mode after duration
    manualModeTimeout = setTimeout(() => {
      motorState.manualMode = false
      console.log('[MOTOR] Manual mode timeout - auto-motor can resume control')
    }, MANUAL_MODE_DURATION)
  } else {
    if (manualModeTimeout) {
      clearTimeout(manualModeTimeout)
      manualModeTimeout = null
    }
  }
}

/**
 * Check if motor is in manual mode
 */
function isManualMode() {
  return motorState.manualMode
}

/**
 * Set motor direction
 * @param {'forward' | 'backward' | 'stop'} direction
 */
function setMotorDirection(direction) {
  if (['forward', 'backward', 'stop'].includes(direction)) {
    motorState.direction = direction
  }
}

/**
 * Set motor throttle
 * @param {number} throttle - 0.0 to 1.0
 */
function setMotorThrottle(throttle) {
  motorState.throttle = Math.max(0, Math.min(1, throttle))
}

/**
 * Get current motor state
 */
function getMotorState() {
  return { ...motorState }
}

/**
 * Calculate motor force
 *
 * Force direction depends on motor direction and context:
 * - Forward with anchor: thrust TOWARD ANCHOR (for retrieval - steers boat to anchor)
 * - Forward without anchor: thrust in direction of heading
 * - Backward: thrust opposite to heading (for deployment)
 *
 * @param {number} boatHeading - Boat heading in degrees (0=North, 90=East)
 * @param {number} [bearingToAnchor] - Bearing to anchor in degrees (optional, for retrieval steering)
 * @param {number} [distanceToAnchor] - Distance to anchor in meters (optional, to stop when close)
 * @param {number} [boatSpeed] - Boat speed in m/s (optional, for velocity-based throttle)
 * @returns {{forceX: number, forceY: number, magnitude: number, direction: string}}
 */
function calculateMotorForce(boatHeading, bearingToAnchor = null, distanceToAnchor = null, boatSpeed = null, rodeDeployed = null) {
  // Distance-based motor control during forward (retrieval) operation
  // IMPORTANT: Don't stop motor just because boat is close to anchor!
  // During active retrieval, motor must keep running to maintain slack for windlass.
  // Only stop when: close to anchor AND rode is nearly fully retrieved
  const STOP_DISTANCE = 3.0     // meters - stop motor completely when very close
  const RAMP_DISTANCE = 20.0    // meters - start ramping down throttle
  const MIN_RODE_FOR_STOP = 3.0 // meters - only stop if rode is less than this

  // Only stop motor when BOTH conditions are met:
  // 1. Boat is close to anchor (< 3m)
  // 2. Rode is nearly fully retrieved (< 3m)
  const closeToAnchor = distanceToAnchor !== null && distanceToAnchor < STOP_DISTANCE
  const rodeNearlyIn = rodeDeployed !== null && rodeDeployed < MIN_RODE_FOR_STOP

  if (motorState.direction === 'forward' && closeToAnchor && rodeNearlyIn) {
    return {
      forceX: 0,
      forceY: 0,
      magnitude: 0,
      direction: 'stop',
      throttle: motorState.throttle,
      reason: 'close_to_anchor'
    }
  }

  // ANCHOR AHEAD CHECK: If anchor is directly ahead of boat, don't motor forward
  // This prevents the boat from trying to motor "through" the anchor when the
  // boat has already reached the anchor position (common when boat weathervanes
  // into wind and anchor happens to be upwind)
  if (motorState.direction === 'forward' && bearingToAnchor !== null) {
    // Calculate angle difference between boat heading and bearing to anchor
    let angleDiff = bearingToAnchor - boatHeading
    // Normalize to -180 to +180
    while (angleDiff > 180) angleDiff -= 360
    while (angleDiff < -180) angleDiff += 360

    // If anchor is within 45° of straight ahead AND boat is close to anchor,
    // stop motor - the boat is already at or past the anchor
    const anchorAhead = Math.abs(angleDiff) < 45
    const veryCloseToAnchor = distanceToAnchor !== null && distanceToAnchor < 5.0

    if (anchorAhead && veryCloseToAnchor) {
      return {
        forceX: 0,
        forceY: 0,
        magnitude: 0,
        direction: 'stop',
        throttle: motorState.throttle,
        reason: 'anchor_ahead'
      }
    }
  }

  if (motorState.direction === 'stop' || motorState.throttle <= 0) {
    return {
      forceX: 0,
      forceY: 0,
      magnitude: 0,
      direction: 'stop',
      throttle: motorState.throttle
    }
  }

  const { forwardThrust, backwardThrust } = config.motor

  // Select thrust based on direction
  const maxThrust = motorState.direction === 'forward' ? forwardThrust : backwardThrust

  // Calculate effective throttle - ramp down when approaching anchor
  let effectiveThrottle = motorState.throttle
  if (motorState.direction === 'forward' && distanceToAnchor !== null && distanceToAnchor < RAMP_DISTANCE) {
    // Quadratic ramp: much more aggressive reduction as we approach
    // At RAMP_DISTANCE: 100%, at STOP_DISTANCE: 5%
    const normalizedDistance = (distanceToAnchor - STOP_DISTANCE) / (RAMP_DISTANCE - STOP_DISTANCE)
    const rampFactor = normalizedDistance * normalizedDistance  // Quadratic for aggressive early reduction
    const minThrottle = 0.05  // 5% minimum throttle in ramp zone (reduced from 20%)
    effectiveThrottle = motorState.throttle * (minThrottle + rampFactor * (1 - minThrottle))

    // Additional velocity-based reduction: if moving fast, reduce throttle more
    // This prevents momentum buildup
    if (boatSpeed !== null && boatSpeed > 0.3) {
      // At 0.3 m/s: no extra reduction
      // At 1.0 m/s: reduce to 20% of calculated throttle
      const speedFactor = Math.max(0.2, 1.0 - (boatSpeed - 0.3) / 0.7 * 0.8)
      effectiveThrottle *= speedFactor
    }
  }

  const thrust = maxThrust * effectiveThrottle

  // Calculate thrust direction
  let thrustDirection

  if (motorState.direction === 'forward' && bearingToAnchor !== null) {
    // RETRIEVAL: Steer toward anchor, not along boat heading
    // This simulates the skipper steering toward the anchor while motoring forward
    thrustDirection = bearingToAnchor * Math.PI / 180
  } else if (motorState.direction === 'backward') {
    // DEPLOYMENT: Reverse thrust - opposite to heading
    const headingRad = boatHeading * Math.PI / 180
    thrustDirection = headingRad + Math.PI
  } else {
    // Default: thrust along boat heading
    const headingRad = boatHeading * Math.PI / 180
    thrustDirection = headingRad
  }

  // Convert to force components
  // Heading 0° = North = +Y, Heading 90° = East = +X
  const forceX = thrust * Math.sin(thrustDirection)
  const forceY = thrust * Math.cos(thrustDirection)

  return {
    forceX,
    forceY,
    magnitude: thrust,
    direction: motorState.direction,
    throttle: motorState.throttle
  }
}

/**
 * Calculate throttle needed to achieve target speed
 * Useful for automatic speed control
 *
 * @param {number} currentSpeed - Current boat speed in m/s
 * @param {number} targetSpeed - Target speed in m/s
 * @param {'forward' | 'backward'} direction - Motor direction
 * @returns {number} - Recommended throttle 0.0 to 1.0
 */
function calculateThrottleForSpeed(currentSpeed, targetSpeed, direction) {
  const { forwardThrust, backwardThrust } = config.motor
  const maxThrust = direction === 'forward' ? forwardThrust : backwardThrust

  // Simple proportional control
  // At terminal velocity: thrust = drag = coeff * v²
  // To achieve target speed, we need thrust ≈ coeff * targetSpeed²

  // Use sideways drag coefficient as rough estimate (anchored boat drifts sideways-ish)
  const dragCoeff = config.waterDrag.sidewaysCoeff || 200

  // Required force to maintain target speed
  const requiredForce = dragCoeff * targetSpeed * targetSpeed

  // Calculate throttle as percentage of max thrust
  const throttle = Math.min(1.0, requiredForce / maxThrust)

  // Reduce throttle if already above target speed
  if (currentSpeed >= targetSpeed) {
    return throttle * 0.5  // Ease off when at speed
  }

  return throttle
}

module.exports = {
  calculateMotorForce,
  setMotorDirection,
  setMotorThrottle,
  getMotorState,
  calculateThrottleForSpeed,
  setManualMode,
  isManualMode
}

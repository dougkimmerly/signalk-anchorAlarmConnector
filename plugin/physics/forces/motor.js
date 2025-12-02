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
 * Force is applied along the boat's heading direction:
 * - Forward: thrust in direction of heading
 * - Backward: thrust opposite to heading
 *
 * @param {number} boatHeading - Boat heading in degrees (0=North, 90=East)
 * @returns {{forceX: number, forceY: number, magnitude: number, direction: string}}
 */
function calculateMotorForce(boatHeading) {
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
  const thrust = maxThrust * motorState.throttle

  // Calculate thrust direction based on heading
  // Forward = along heading, Backward = opposite to heading
  const headingRad = boatHeading * Math.PI / 180
  let thrustDirection = headingRad

  if (motorState.direction === 'backward') {
    // Reverse thrust - opposite to heading
    thrustDirection = headingRad + Math.PI
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

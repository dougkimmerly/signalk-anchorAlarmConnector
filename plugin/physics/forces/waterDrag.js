/**
 * Water Drag Force Module
 *
 * Calculates water resistance force opposing boat velocity.
 * Uses quadratic drag model with DIRECTIONAL coefficients based on
 * the angle between movement direction and boat heading.
 *
 * Hull shape means:
 * - Forward motion (movement = heading): lowest drag, highest speed
 * - Backward motion (movement = heading + 180°): medium drag
 * - Sideways motion (movement = heading ± 90°): highest drag, lowest speed
 *
 * This is a PURE FUNCTION with no state or dependencies.
 */

const { config } = require('../../config/simulationConfig')

/**
 * Convert degrees to radians
 */
function degreesToRadians(degrees) {
  return degrees * Math.PI / 180
}

/**
 * Calculate effective drag coefficient based on movement direction vs heading
 *
 * @param {number} movementAngle - Direction of movement in degrees (0=North, 90=East)
 * @param {number} boatHeading - Boat heading in degrees (0=North, 90=East)
 * @returns {number} - Effective drag coefficient
 */
function getDirectionalDragCoefficient(movementAngle, boatHeading) {
  const { forwardCoeff, backwardCoeff, sidewaysCoeff } = config.waterDrag

  // Calculate angle difference between movement and heading
  // 0° = moving forward, 180° = moving backward, 90° = moving sideways
  let angleDiff = movementAngle - boatHeading

  // Normalize to -180 to +180
  while (angleDiff > 180) angleDiff -= 360
  while (angleDiff < -180) angleDiff += 360

  const absAngle = Math.abs(angleDiff)

  // Interpolate between coefficients based on angle
  // 0-45°: forward to forward/sideways blend
  // 45-135°: sideways dominant
  // 135-180°: backward

  if (absAngle <= 45) {
    // Forward quadrant: interpolate forward to sideways
    const t = absAngle / 45
    return forwardCoeff + (sidewaysCoeff - forwardCoeff) * t * 0.5
  } else if (absAngle <= 135) {
    // Sideways quadrant: mostly sideways with some forward/backward blend
    return sidewaysCoeff
  } else {
    // Backward quadrant: interpolate sideways to backward
    const t = (absAngle - 135) / 45
    return sidewaysCoeff + (backwardCoeff - sidewaysCoeff) * t
  }
}

/**
 * Calculate water drag force with directional coefficients
 *
 * @param {number} velocityX - Boat velocity in X direction (m/s, positive = East)
 * @param {number} velocityY - Boat velocity in Y direction (m/s, positive = North)
 * @param {number} boatHeading - Boat heading in degrees (0=North, 90=East)
 * @returns {{forceX: number, forceY: number, coefficient: number}} - Drag force components in Newtons
 *
 * Physics:
 * - Drag opposes velocity direction
 * - Magnitude proportional to velocity squared (quadratic drag)
 * - Coefficient varies based on movement direction vs heading
 * - F = -v * |v| * coefficient(angle)
 */
function calculateWaterDrag(velocityX, velocityY, boatHeading = 0) {
  // Calculate speed (magnitude of velocity)
  const speed = Math.sqrt(velocityX * velocityX + velocityY * velocityY)

  if (speed < 0.001) {
    // Nearly stationary - no drag
    return { forceX: 0, forceY: 0, coefficient: config.waterDrag.forwardCoeff }
  }

  // Calculate movement direction (angle of velocity vector)
  // atan2(x, y) because our coordinate system is 0°=North, 90°=East
  let movementAngle = Math.atan2(velocityX, velocityY) * 180 / Math.PI

  // Normalize to 0-360
  if (movementAngle < 0) movementAngle += 360

  // Get directional drag coefficient
  const coefficient = getDirectionalDragCoefficient(movementAngle, boatHeading)

  // Quadratic drag: F = -v * |v| * coefficient
  // This naturally opposes motion and increases with speed squared
  const forceX = -velocityX * speed * coefficient
  const forceY = -velocityY * speed * coefficient

  return { forceX, forceY, coefficient }
}

/**
 * Calculate terminal velocity for a given force and drag coefficient
 *
 * At terminal velocity: applied force = drag force
 * F_applied = v² * coefficient
 * v_terminal = sqrt(F_applied / coefficient)
 *
 * @param {number} appliedForce - Force in Newtons
 * @param {number} coefficient - Drag coefficient (optional, uses forward by default)
 * @returns {number} - Terminal velocity in m/s
 */
function calculateTerminalVelocity(appliedForce, coefficient = null) {
  const coeff = coefficient || config.waterDrag.forwardCoeff
  return Math.sqrt(Math.abs(appliedForce) / coeff)
}

/**
 * Calculate terminal velocities for all directions
 *
 * @param {number} appliedForce - Force in Newtons
 * @returns {{forward: number, backward: number, sideways: number}} - Terminal velocities in m/s
 */
function calculateDirectionalTerminalVelocities(appliedForce) {
  const { forwardCoeff, backwardCoeff, sidewaysCoeff } = config.waterDrag
  return {
    forward: Math.sqrt(Math.abs(appliedForce) / forwardCoeff),
    backward: Math.sqrt(Math.abs(appliedForce) / backwardCoeff),
    sideways: Math.sqrt(Math.abs(appliedForce) / sidewaysCoeff)
  }
}

/**
 * Check if boat is approximately at terminal velocity
 *
 * @param {number} velocityX - Current X velocity
 * @param {number} velocityY - Current Y velocity
 * @param {number} forceX - Applied force X component
 * @param {number} forceY - Applied force Y component
 * @param {number} coefficient - Current drag coefficient
 * @returns {boolean} - True if at terminal velocity (within 5%)
 */
function isAtTerminalVelocity(velocityX, velocityY, forceX, forceY, coefficient = null) {
  const appliedForce = Math.sqrt(forceX * forceX + forceY * forceY)
  const terminalSpeed = calculateTerminalVelocity(appliedForce, coefficient)
  const currentSpeed = Math.sqrt(velocityX * velocityX + velocityY * velocityY)

  if (terminalSpeed < 0.001) return true  // No force applied
  // Within 5% of terminal velocity
  return Math.abs(currentSpeed - terminalSpeed) / terminalSpeed < 0.05
}

module.exports = {
  calculateWaterDrag,
  calculateTerminalVelocity,
  calculateDirectionalTerminalVelocities,
  isAtTerminalVelocity,
  getDirectionalDragCoefficient
}

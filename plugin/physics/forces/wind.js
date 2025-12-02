/**
 * Wind Force Module
 *
 * Calculates wind force on the boat based on wind speed and direction.
 * Also calculates heading torque for weathervane effect.
 *
 * DIRECTION CONVENTION:
 * - windDirection is the compass direction the wind comes FROM
 * - 0° = wind from North (pushes South)
 * - 90° = wind from East (pushes West)
 * - 180° = wind from South (pushes North)
 * - 270° = wind from West (pushes East)
 *
 * COORDINATE SYSTEM:
 * - X axis: positive = East
 * - Y axis: positive = North
 * - Angles: 0° = North, 90° = East, measured clockwise
 */

const { config } = require('../../config/simulationConfig')

/**
 * Convert wind direction (FROM) to push direction (TO)
 * Wind from South (180°) pushes to North (0°)
 *
 * @param {number} windFromDirection - Direction wind comes FROM in degrees
 * @returns {number} - Direction wind pushes TO in degrees
 */
function windFromToPushDirection(windFromDirection) {
  return (windFromDirection + 180) % 360
}

/**
 * Convert degrees to radians
 */
function degreesToRadians(degrees) {
  return degrees * Math.PI / 180
}

/**
 * Convert knots to meters per second
 */
function knotsToMs(knots) {
  return knots * 0.51444
}

/**
 * Calculate wind force on the boat
 *
 * @param {number} windSpeed - Wind speed in knots
 * @param {number} windDirection - Direction wind comes FROM in degrees
 * @param {number} boatHeading - Current boat heading in degrees (for future angle-of-attack)
 * @returns {{forceX: number, forceY: number, pushDirection: number}} - Force in Newtons and push direction
 *
 * Physics:
 * - F = 0.5 * ρ * A * Cd * v²
 * - ρ = air density (1.2 kg/m³)
 * - A = windage area (30 m²)
 * - Cd = drag coefficient (1.0)
 * - v = wind speed in m/s
 */
function calculateWindForce(windSpeed, windDirection, boatHeading = 0) {
  const { airDensity, windageArea, dragCoefficient } = config.wind

  // Convert wind speed from knots to m/s
  const windSpeedMs = knotsToMs(windSpeed)

  // Calculate force magnitude using aerodynamic drag formula
  // F = 0.5 * ρ * A * Cd * v²
  const forceMagnitude = 0.5 * airDensity * windageArea * dragCoefficient * windSpeedMs * windSpeedMs

  // Convert wind FROM direction to push direction
  const pushDirection = windFromToPushDirection(windDirection)
  const pushAngleRad = degreesToRadians(pushDirection)

  // Decompose into X (East) and Y (North) components
  // In our coordinate system:
  // - sin(angle) gives East component (X)
  // - cos(angle) gives North component (Y)
  const forceX = forceMagnitude * Math.sin(pushAngleRad)
  const forceY = forceMagnitude * Math.cos(pushAngleRad)

  return {
    forceX,
    forceY,
    forceMagnitude,
    pushDirection
  }
}

/**
 * Calculate heading torque for weathervane effect
 *
 * When not anchored, boat tends to point into the wind (weathervane).
 * This creates a torque that rotates the boat.
 *
 * @param {number} windDirection - Direction wind comes FROM in degrees
 * @param {number} boatHeading - Current boat heading in degrees
 * @param {number} windSpeed - Wind speed in knots (affects torque strength)
 * @returns {number} - Torque value (positive = clockwise rotation)
 */
function calculateWeathervvaneTorque(windDirection, boatHeading, windSpeed) {
  const { weathervaneTorque } = config.heading

  // Boat wants to point INTO the wind (toward wind source)
  // So target heading = windDirection (where wind comes from)
  const targetHeading = windDirection

  // Calculate angle difference (shortest path)
  let angleDiff = targetHeading - boatHeading

  // Normalize to -180 to +180
  while (angleDiff > 180) angleDiff -= 360
  while (angleDiff < -180) angleDiff += 360

  // Torque proportional to angle difference and wind speed
  // Stronger wind = faster rotation toward wind
  const windFactor = Math.min(windSpeed / 20, 1)  // Normalize to 0-1
  const torque = angleDiff * weathervaneTorque * windFactor / 180

  return torque
}

/**
 * Calculate heading torque when anchored
 *
 * When anchored, boat tends to point toward the anchor due to rode tension.
 *
 * @param {number} anchorBearing - Bearing to anchor from boat in degrees
 * @param {number} boatHeading - Current boat heading in degrees
 * @returns {number} - Torque value (positive = clockwise rotation)
 */
function calculateAnchorTorque(anchorBearing, boatHeading) {
  const { anchorTorque } = config.heading

  // Boat wants to point toward anchor
  const targetHeading = anchorBearing

  // Calculate angle difference (shortest path)
  let angleDiff = targetHeading - boatHeading

  // Normalize to -180 to +180
  while (angleDiff > 180) angleDiff -= 360
  while (angleDiff < -180) angleDiff += 360

  // Torque proportional to angle difference
  const torque = angleDiff * anchorTorque / 180

  return torque
}

/**
 * Calculate combined heading torque when anchored
 *
 * When anchored, the boat experiences two competing influences:
 * 1. Rode tension pulling bow toward anchor (primary)
 * 2. Wind pushing boat to weathervane (secondary)
 *
 * The rode tension dominates, but wind still has some effect.
 * This creates realistic behavior where the boat points mostly toward
 * the anchor but swings slightly with wind shifts.
 *
 * @param {number} anchorBearing - Bearing to anchor from boat in degrees
 * @param {number} windDirection - Direction wind comes FROM in degrees
 * @param {number} boatHeading - Current boat heading in degrees
 * @param {number} windSpeed - Wind speed in knots
 * @param {number} distanceToAnchor - Distance to anchor in meters (affects tension)
 * @param {number} rodeDeployed - Amount of rode deployed in meters
 * @returns {{anchorTorque: number, windTorque: number, totalTorque: number}}
 */
function calculateAnchoredHeadingTorque(anchorBearing, windDirection, boatHeading, windSpeed, distanceToAnchor = 0, rodeDeployed = 0) {
  // Calculate individual torques
  const anchorT = calculateAnchorTorque(anchorBearing, boatHeading)
  const windT = calculateWeathervvaneTorque(windDirection, boatHeading, windSpeed)

  // Rode tension influence increases when:
  // - Distance to anchor is closer to rode length (chain is tight)
  // - More rode is deployed (stronger constraint)
  //
  // When chain is slack (distance << rode), wind has more influence
  // When chain is tight (distance ~= rode), anchor dominates

  let tensionFactor = 0.8  // Default: anchor dominates at 80%

  if (rodeDeployed > 0 && distanceToAnchor > 0) {
    // Calculate slack ratio: 0 = at limit, 1 = lots of slack
    const slackRatio = Math.max(0, (rodeDeployed - distanceToAnchor) / rodeDeployed)

    // When slack is low (chain tight), anchor dominates more
    // When slack is high (chain loose), wind has more influence
    // Range: 0.6 (lots of slack) to 0.95 (very tight)
    tensionFactor = 0.6 + (1 - slackRatio) * 0.35
  }

  const windFactor = 1 - tensionFactor

  // Combine torques
  const totalTorque = anchorT * tensionFactor + windT * windFactor

  return {
    anchorTorque: anchorT * tensionFactor,
    windTorque: windT * windFactor,
    totalTorque,
    tensionFactor,
    windFactor
  }
}

/**
 * Get expected movement direction for a given wind
 * Useful for test validation
 *
 * @param {number} windDirection - Direction wind comes FROM in degrees
 * @returns {{expectedBearing: number, description: string}}
 */
function getExpectedMovement(windDirection) {
  const pushDirection = windFromToPushDirection(windDirection)

  const directions = {
    0: 'North',
    45: 'Northeast',
    90: 'East',
    135: 'Southeast',
    180: 'South',
    225: 'Southwest',
    270: 'West',
    315: 'Northwest'
  }

  // Find closest named direction
  const closest = Object.keys(directions)
    .map(Number)
    .reduce((prev, curr) =>
      Math.abs(curr - pushDirection) < Math.abs(prev - pushDirection) ? curr : prev
    )

  return {
    expectedBearing: pushDirection,
    description: `Wind from ${windDirection}° pushes boat ${directions[closest]} (${pushDirection}°)`
  }
}

module.exports = {
  calculateWindForce,
  calculateWeathervvaneTorque,
  calculateAnchorTorque,
  calculateAnchoredHeadingTorque,
  windFromToPushDirection,
  getExpectedMovement,
  knotsToMs,
  degreesToRadians
}

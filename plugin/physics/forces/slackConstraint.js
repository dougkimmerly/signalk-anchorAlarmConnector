/**
 * Slack Constraint Module
 *
 * Implements "dead stop" behavior using velocity constraint, not force,
 * plus a catenary restoring force from chain weight.
 *
 * CRITICAL: The CHAIN CONTROLLER (ESP32) calculates and publishes slack
 * to SignalK. The simulator only READS this value - it does NOT calculate slack.
 *
 * BEHAVIOR:
 * 1. Chain Weight Force (catenary effect):
 *    - When chain lifts off seabed, its weight pulls boat toward anchor
 *    - Force scales with how much chain is suspended (depth - slack)
 *    - At slack=0, full depth of chain is suspended = max force
 *    - At slack>=depth, all chain on seabed = no force
 *    - This creates natural "bounce back" toward anchor
 *
 * 2. Velocity Constraint (dead stop):
 *    - slack > buffer: No constraint, boat moves freely
 *    - slack <= buffer: Velocity constraint active - boat cannot move away from anchor
 *    - The buffer prevents overshoot by activating slightly before fully taut
 *
 * The chain weight force is applied BEFORE the velocity constraint, so if
 * the chain weight exceeds opposing forces (wind), the boat moves toward anchor.
 */

const { config } = require('../../config/simulationConfig')

/**
 * Check if slack constraint should be active
 *
 * @param {number} slack - Chain slack in meters (from chain controller via SignalK)
 * @returns {boolean} - True if constraint should be active (slack <= buffer)
 */
function isConstraintActive(slack) {
  const buffer = config.slackConstraint?.activationBuffer ?? 0
  return slack <= buffer
}

/**
 * Calculate tension ratio for logging/display
 *
 * @param {number} slack - Chain slack in meters
 * @param {number} depth - Water depth in meters
 * @returns {number} - Tension ratio: 0 = loose, 1 = taut, >1 = over-extended
 */
function calculateTensionRatio(slack, depth) {
  if (slack >= depth) return 0
  return (depth - slack) / depth
}

/**
 * Calculate chain weight restoring force (catenary effect)
 *
 * When chain lifts off the seabed, its suspended weight creates a force
 * pulling the boat toward the anchor. This provides natural "bounce back"
 * when the chain becomes taut.
 *
 * Physics:
 * - Suspended chain length = depth - slack (clamped to 0)
 * - Force = suspendedLength * chainWeightPerMeter * gravity
 * - Force direction: toward anchor (along bearing to anchor)
 *
 * @param {number} slack - Chain slack in meters (from chain controller)
 * @param {number} depth - Water depth in meters
 * @param {number} bearingToAnchor - Bearing to anchor in degrees (0=North, 90=East)
 * @returns {{forceX: number, forceY: number, magnitude: number, suspendedLength: number}}
 */
function calculateChainWeightForce(slack, depth, bearingToAnchor) {
  const chainWeightPerMeter = config.slackConstraint?.chainWeightPerMeter ?? 2.5
  const gravity = config.slackConstraint?.gravity ?? 9.81

  // Calculate how much chain is suspended (lifted off seabed)
  // When slack >= depth, all chain is on seabed (no suspended weight)
  // When slack = 0, full depth of chain is suspended
  // When slack < 0, still only depth of chain can be suspended
  const suspendedLength = Math.max(0, Math.min(depth, depth - slack))

  if (suspendedLength <= 0) {
    return { forceX: 0, forceY: 0, magnitude: 0, suspendedLength: 0 }
  }

  // Force magnitude = weight of suspended chain
  const magnitude = suspendedLength * chainWeightPerMeter * gravity

  // Force direction: toward anchor
  const bearingRad = bearingToAnchor * Math.PI / 180
  const forceX = magnitude * Math.sin(bearingRad)  // East component
  const forceY = magnitude * Math.cos(bearingRad)  // North component

  return {
    forceX,
    forceY,
    magnitude,
    suspendedLength
  }
}

module.exports = {
  isConstraintActive,
  calculateTensionRatio,
  calculateChainWeightForce
}

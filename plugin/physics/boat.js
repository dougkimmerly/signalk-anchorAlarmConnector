/**
 * Boat State Module
 *
 * Manages boat state (position, velocity, heading) with encapsulation.
 * Provides methods for applying forces and updating state.
 *
 * COORDINATE SYSTEM:
 * - Position: latitude (North+), longitude (East+)
 * - Velocity: velocityX (East+, m/s), velocityY (North+, m/s)
 * - Heading: degrees, 0° = North, clockwise
 * - Angular velocity: degrees/second, positive = clockwise
 */

const { config } = require('../config/simulationConfig')

/**
 * Create a new boat state object
 *
 * @param {object} initialState - Optional initial state override
 * @returns {object} - Boat state object with methods
 */
function createBoat(initialState = {}) {
  // Initialize state from config, with overrides
  const state = {
    // Position
    latitude: initialState.latitude ?? config.initial.latitude,
    longitude: initialState.longitude ?? config.initial.longitude,

    // Linear velocity (m/s)
    velocityX: initialState.velocityX ?? config.initial.velocityX,
    velocityY: initialState.velocityY ?? config.initial.velocityY,

    // Heading and rotation
    heading: initialState.heading ?? config.initial.heading,
    angularVelocity: initialState.angularVelocity ?? config.initial.angularVelocity,

    // Accumulated forces for this timestep
    accumulatedForceX: 0,
    accumulatedForceY: 0,
    accumulatedTorque: 0,

    // Anchor state (read from external source)
    isAnchored: false,
    anchorLatitude: null,
    anchorLongitude: null,

    // Velocity constraint (for slack constraint - "dead stop" behavior)
    // When set, velocity component away from anchor is zeroed
    velocityConstraint: {
      active: false,
      bearingToAnchor: 0,  // degrees
    },
  }

  return {
    /**
     * Get current state (read-only copy)
     */
    getState() {
      return {
        latitude: state.latitude,
        longitude: state.longitude,
        velocityX: state.velocityX,
        velocityY: state.velocityY,
        speed: Math.sqrt(state.velocityX ** 2 + state.velocityY ** 2),
        heading: state.heading,
        angularVelocity: state.angularVelocity,
        isAnchored: state.isAnchored,
        anchorLatitude: state.anchorLatitude,
        anchorLongitude: state.anchorLongitude,
      }
    },

    /**
     * Apply a force to the boat (accumulates until update())
     *
     * @param {number} forceX - Force in X direction (Newtons, East+)
     * @param {number} forceY - Force in Y direction (Newtons, North+)
     */
    applyForce(forceX, forceY) {
      state.accumulatedForceX += forceX
      state.accumulatedForceY += forceY
    },

    /**
     * Apply a torque to the boat (affects heading rotation)
     *
     * @param {number} torque - Torque value (positive = clockwise)
     */
    applyTorque(torque) {
      state.accumulatedTorque += torque
    },

    /**
     * Update boat state based on accumulated forces
     * Call this once per physics timestep
     *
     * @param {number} dt - Time step in seconds (defaults to config)
     * @returns {object} - State changes for logging
     */
    update(dt = config.physics.dt) {
      const mass = config.physics.boatMass

      // Calculate acceleration from forces (F = ma)
      const accelX = state.accumulatedForceX / mass
      const accelY = state.accumulatedForceY / mass

      // Update velocity (v = v + a * dt)
      state.velocityX += accelX * dt
      state.velocityY += accelY * dt

      // ============================================
      // VELOCITY CONSTRAINT (dead stop behavior)
      // Zero out velocity component moving away from anchor
      // ============================================
      if (state.velocityConstraint.active) {
        const bearingRad = state.velocityConstraint.bearingToAnchor * Math.PI / 180
        const toAnchorX = Math.sin(bearingRad)  // East component (unit vector toward anchor)
        const toAnchorY = Math.cos(bearingRad)  // North component

        // Project velocity onto anchor direction
        // Positive = moving toward anchor, Negative = moving away
        const velocityTowardAnchor = state.velocityX * toAnchorX + state.velocityY * toAnchorY

        // If moving away from anchor (negative projection), zero that component
        if (velocityTowardAnchor < 0) {
          // Remove the "away" component, keep perpendicular movement
          state.velocityX -= velocityTowardAnchor * toAnchorX
          state.velocityY -= velocityTowardAnchor * toAnchorY
        }
      }

      // Calculate position delta in meters
      const deltaX = state.velocityX * dt  // meters East
      const deltaY = state.velocityY * dt  // meters North

      // Convert to lat/lon
      const deltaLat = deltaY * config.physics.metersToLat
      const deltaLon = deltaX * config.physics.metersToLon

      // Update position
      state.latitude += deltaLat
      state.longitude += deltaLon

      // Update heading with angular velocity and damping
      // Torque affects angular velocity, with time-scaled damping
      const angularAccel = state.accumulatedTorque * dt  // Torque scaled by timestep
      state.angularVelocity += angularAccel

      // Apply damping - time-based for consistent behavior across different dt
      // damping of 0.85 means lose 85% of angular velocity per second
      // Per step: (1 - damping)^(1/dt) retention per second
      // Simplified: (1 - damping * dt) per step for small dt
      const dampingFactor = Math.pow(1 - config.heading.rotationalDamping, dt * 20)  // Scale to make 0.85 reasonable
      state.angularVelocity *= dampingFactor

      // Limit angular velocity to prevent wild spinning
      const maxAngVel = config.heading.maxAngularVelocity || 10
      state.angularVelocity = Math.max(-maxAngVel, Math.min(maxAngVel, state.angularVelocity))

      // Update heading
      state.heading += state.angularVelocity * dt
      state.heading = ((state.heading % 360) + 360) % 360  // Normalize 0-360

      // Store changes for logging before clearing
      const changes = {
        accelX,
        accelY,
        deltaX,
        deltaY,
        forceX: state.accumulatedForceX,
        forceY: state.accumulatedForceY,
        torque: state.accumulatedTorque,
      }

      // Clear accumulated forces for next timestep
      state.accumulatedForceX = 0
      state.accumulatedForceY = 0
      state.accumulatedTorque = 0

      return changes
    },

    /**
     * Set anchor state (called when anchor position is known)
     *
     * @param {number|null} latitude - Anchor latitude (null to clear)
     * @param {number|null} longitude - Anchor longitude
     */
    setAnchor(latitude, longitude) {
      if (latitude === null || longitude === null) {
        state.isAnchored = false
        state.anchorLatitude = null
        state.anchorLongitude = null
      } else {
        state.isAnchored = true
        state.anchorLatitude = latitude
        state.anchorLongitude = longitude
      }
    },

    /**
     * Calculate bearing to anchor
     *
     * @returns {number|null} - Bearing in degrees, or null if not anchored
     */
    getBearingToAnchor() {
      if (!state.isAnchored) return null

      const deltaLat = state.anchorLatitude - state.latitude
      const deltaLon = state.anchorLongitude - state.longitude

      // Convert to meters
      const deltaY = deltaLat / config.physics.metersToLat
      const deltaX = deltaLon / config.physics.metersToLon

      // Calculate bearing (atan2 returns radians, 0 = East)
      const angleRad = Math.atan2(deltaX, deltaY)  // Note: atan2(x, y) for North-based bearing
      let bearing = angleRad * 180 / Math.PI

      // Normalize to 0-360
      bearing = ((bearing % 360) + 360) % 360

      return bearing
    },

    /**
     * Calculate distance to anchor
     *
     * @returns {number|null} - Distance in meters, or null if not anchored
     */
    getDistanceToAnchor() {
      if (!state.isAnchored) return null

      const deltaLat = state.anchorLatitude - state.latitude
      const deltaLon = state.anchorLongitude - state.longitude

      // Convert to meters
      const deltaY = deltaLat / config.physics.metersToLat
      const deltaX = deltaLon / config.physics.metersToLon

      return Math.sqrt(deltaX ** 2 + deltaY ** 2)
    },

    /**
     * Reset boat state to initial values
     */
    reset() {
      state.latitude = config.initial.latitude
      state.longitude = config.initial.longitude
      state.velocityX = config.initial.velocityX
      state.velocityY = config.initial.velocityY
      state.heading = config.initial.heading
      state.angularVelocity = config.initial.angularVelocity
      state.accumulatedForceX = 0
      state.accumulatedForceY = 0
      state.accumulatedTorque = 0
      state.isAnchored = false
      state.anchorLatitude = null
      state.anchorLongitude = null
    },

    /**
     * Set position directly (for testing or external control)
     */
    setPosition(latitude, longitude) {
      state.latitude = latitude
      state.longitude = longitude
    },

    /**
     * Set velocity directly (for testing)
     */
    setVelocity(velocityX, velocityY) {
      state.velocityX = velocityX
      state.velocityY = velocityY
    },

    /**
     * Set heading directly
     */
    setHeading(heading) {
      state.heading = ((heading % 360) + 360) % 360
    },

    /**
     * Set velocity constraint (for dead stop behavior)
     * When active, velocity component away from anchor is zeroed
     *
     * @param {boolean} active - Whether constraint is active
     * @param {number} bearingToAnchor - Bearing to anchor in degrees (only used if active)
     */
    setVelocityConstraint(active, bearingToAnchor = 0) {
      state.velocityConstraint.active = active
      state.velocityConstraint.bearingToAnchor = bearingToAnchor
    },
  }
}

module.exports = {
  createBoat
}

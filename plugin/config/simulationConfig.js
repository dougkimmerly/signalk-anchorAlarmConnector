/**
 * Simulation Configuration
 *
 * Central configuration for the physics simulation.
 * All tunable parameters and force toggles in one place.
 *
 * IMPORTANT: This config can be modified at runtime via HTTP endpoints
 * to enable isolated testing of individual forces.
 */

const config = {
  // Force enable/disable flags - for isolated testing
  forces: {
    wind: {
      enabled: true,
      logForce: true,
      description: 'Wind pushing boat based on speed and direction'
    },
    waterDrag: {
      enabled: true,
      logForce: true,
      description: 'Water resistance proportional to velocity squared'
    },
    motor: {
      enabled: true,   // Phase 4 - enabled for testing
      logForce: true,
      description: 'Motor thrust forward/backward along heading'
    },
    slackConstraint: {
      enabled: true,  // Now enabled for Phase 3 testing
      logForce: true,
      description: 'Prevents boat from exceeding rope length'
    }
  },

  // Physics constants
  physics: {
    boatMass: 15875,           // kg (35,000 lbs)
    dt: 0.05,                  // Time step in seconds (20 Hz)

    // Coordinate conversion (approximate at lat 43.6°)
    metersToLat: 0.000009,     // Latitude degrees per meter
    metersToLon: 0.0000125,    // Longitude degrees per meter
  },

  // Water drag parameters - DIRECTIONAL based on movement vs heading
  // Hull shape means drag varies significantly with direction:
  // - Forward: streamlined bow, lowest drag
  // - Backward: blunt stern, medium drag
  // - Sideways: full hull profile, highest drag
  waterDrag: {
    // Directional coefficients tuned for terminal velocity in 10kn wind (~476N):
    // v_terminal = sqrt(F_wind / coefficient)
    forwardCoeff: 28,          // Forward: ~4.1 m/s = ~8 knots
    backwardCoeff: 112,        // Backward: ~2.1 m/s = ~4 knots
    sidewaysCoeff: 449,        // Sideways: ~1.0 m/s = ~2 knots

    // Legacy single coefficient (kept for compatibility, not used if directional enabled)
    coefficient: 200.0,
  },

  // Wind parameters
  wind: {
    initialSpeed: 10,          // knots
    initialDirection: 180,     // degrees (180 = from South, pushes North)

    // Wind variation - enabled for realistic simulation
    gustEnabled: true,         // Smooth speed variations
    gustMagnitude: 3,          // ±3 knots variation around base speed

    shiftEnabled: true,        // Direction oscillation and shifts
    oscillationMagnitude: 5,   // ±5 degrees continuous swing (causes boat to swing)
    oscillationPeriod: 30000,  // 30 second swing period
    shiftMagnitude: 15,        // ±15 degrees for major shifts
    shiftInterval: 60000,      // 60 seconds between major shifts

    // Aerodynamic parameters
    airDensity: 1.2,           // kg/m³
    windageArea: 30,           // m² (sailboat windage)
    dragCoefficient: 1.0,      // Cd for flat plate approximation
    // Formula: F_wind = 0.5 * ρ * A * Cd * v²
  },

  // Boat heading behavior
  heading: {
    // Rotational dynamics - tuned to avoid oscillation while maintaining responsiveness
    // Damping at 0.5 provides good balance: some overshoot but quick settling
    // Torques increased to ensure boat rotates at reasonable speed
    rotationalDamping: 0.5,    // Damping coefficient (0.5 = light damping, good response)
    weathervaneTorque: 60,     // Torque strength for wind weathervaning
    anchorTorque: 80,          // Torque strength for anchor orientation
    maxAngularVelocity: 30,    // Max degrees/second rotation (realistic for anchored boat)

    // Heading modes
    // - When anchored: boat tends to point toward anchor
    // - When free: boat tends to point into wind (weathervane)
  },

  // Motor parameters (for Phase 4)
  motor: {
    forwardThrust: 8000,       // N at full throttle (54 HP motor ~ 8000-10000 N bollard pull)
    backwardThrust: 5000,      // N at full throttle (reverse ~60% of forward)
    targetSpeedForward: 1.5,   // m/s target speed toward anchor (~3 knots)
    targetSpeedBackward: 0.8,  // m/s target speed away from anchor (~1.5 knots)

    // Auto-motor control thresholds
    autoMotorEnabled: true,    // Enable automatic motor engagement
    deployMinSpeed: 0.3,       // m/s - engage motorBackward if below this during deployment
    deployTargetSpeed: 0.8,    // m/s - target speed during deployment (~1.5 knots)
    retrieveSlackTarget: 1.0,  // meters - maintain this much slack during retrieval

    // Throttle ramp control - faster response for strong winds
    throttleRampRate: 0.3,     // Max throttle change per second (0.3 = ~3.3 seconds to full)
    retrieveMinThrottle: 0.2,  // Starting throttle for retrieval (20%)
    retrieveMaxThrottle: 0.9,  // Max auto-throttle for retrieval (90%)
    deployMinThrottle: 0.2,    // Starting throttle for deployment (20%)
    deployMaxThrottle: 0.9,    // Max auto-throttle for deployment (90%)
  },

  // Slack constraint parameters (Phase 3)
  slackConstraint: {
    // "Dead stop" model - firm constraint with minimal bounce
    // High damping kills velocity, low stiffness prevents spring-back
    constraintStiffness: 500,    // N/m - low spring constant (minimal bounce-back)
    constraintDamping: 25000,    // N/(m/s) - very high damping (kills velocity fast)
    softZone: 0.5,               // meters - not currently used

    // Buffer threshold: apply constraint slightly before slack reaches 0
    // This prevents overshoot due to momentum
    // e.g., 0.5 means constraint activates when slack <= 0.5m
    activationBuffer: 0.5,       // meters - constraint activates at slack <= this value

    // Chain weight parameters for catenary restoring force
    // When chain lifts off seabed, its weight pulls boat toward anchor
    chainWeightPerMeter: 2.5,    // kg/m - typical 10mm chain ~2.5 kg/m
    gravity: 9.81,               // m/s² - gravitational acceleration
    // Max force = chainWeightPerMeter * depth * gravity
    // e.g., 3m depth: 2.5 * 3 * 9.81 = 73.6N pulling toward anchor
  },

  // Logging configuration
  logging: {
    enabled: true,
    logForces: true,           // Log individual force contributions
    logInterval: 20,           // Log every N iterations (20 = once per second at 20Hz)
    logPosition: true,
    logVelocity: true,
    logHeading: true,
  },

  // Initial boat position (for testing)
  initial: {
    latitude: 43.59738,
    longitude: -79.5073,
    heading: 180,              // degrees (pointing South, into wind from South)
    velocityX: 0,
    velocityY: 0,
    angularVelocity: 0,
  },

  // Test environment
  environment: {
    depth: 3.0,                // meters (base depth without tide)
    bowHeight: 2.0,            // meters above waterline (for scope calculation)
  },

  // Tide simulation (Marsh Harbor, Bahamas)
  tides: {
    enabled: true,             // Enable tide simulation
    location: 'Marsh Harbor',  // Reference location
    M2_PERIOD: 44712,          // seconds (12.42 hours - M2 lunar semi-diurnal)
    MEAN_HEIGHT: 0.52,         // meters - average tide height
    AMPLITUDE: 0.36,           // meters - tide swing (high=0.88m, low=0.16m)
    epochOffset: 0             // seconds - phase offset for syncing with real tides
  }
}

/**
 * Get current configuration (returns a copy to prevent accidental mutation)
 */
function getConfig() {
  return JSON.parse(JSON.stringify(config))
}

/**
 * Update configuration at runtime
 * @param {object} updates - Partial config object to merge
 */
function updateConfig(updates) {
  deepMerge(config, updates)
}

/**
 * Reset configuration to defaults
 */
function resetConfig() {
  // This would need to store original values - for now just log
  console.log('Config reset requested - not yet implemented')
}

/**
 * Deep merge helper
 */
function deepMerge(target, source) {
  for (const key in source) {
    if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
      if (!target[key]) target[key] = {}
      deepMerge(target[key], source[key])
    } else {
      target[key] = source[key]
    }
  }
}

/**
 * Check if a force is enabled
 */
function isForceEnabled(forceName) {
  return config.forces[forceName]?.enabled ?? false
}

/**
 * Enable or disable a force
 */
function setForceEnabled(forceName, enabled) {
  if (config.forces[forceName]) {
    config.forces[forceName].enabled = enabled
    console.log(`Force '${forceName}' ${enabled ? 'enabled' : 'disabled'}`)
  }
}

module.exports = {
  config,
  getConfig,
  updateConfig,
  resetConfig,
  isForceEnabled,
  setForceEnabled
}

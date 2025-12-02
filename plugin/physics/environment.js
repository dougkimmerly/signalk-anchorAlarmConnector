/**
 * Environment Module
 *
 * Manages environmental conditions: wind, depth, tides, etc.
 * Single source of truth for all environmental variables.
 *
 * The simulator CREATES and CONTROLS these values.
 * They are published to SignalK for consumption by other systems.
 */

const { config, updateConfig } = require('../config/simulationConfig')
const { createTideSimulator } = require('./tides')

/**
 * Create an environment state manager
 *
 * @param {object} initialState - Optional initial state override
 * @returns {object} - Environment state object with methods
 */
function createEnvironment(initialState = {}) {
  // Create tide simulator
  const tideSimulator = createTideSimulator()

  const state = {
    // Wind
    windSpeed: initialState.windSpeed ?? config.wind.initialSpeed,
    windDirection: initialState.windDirection ?? config.wind.initialDirection,

    // Water - base depth without tide
    baseDepth: initialState.depth ?? config.environment.depth,

    // Timing for wind variation
    lastGustTime: Date.now(),
    lastShiftTime: Date.now(),
    lastUpdateTime: Date.now(),

    // Smooth wind variation state (for natural transitions)
    gustTarget: 0,           // Current gust target (deviation from base speed)
    gustCurrent: 0,          // Current gust value (smoothly approaches target)
    directionOscillation: 0, // Small continuous oscillation
    oscillationPhase: 0,     // Phase for sinusoidal oscillation
  }

  return {
    /**
     * Get current environment state
     */
    getState() {
      const tidesEnabled = config.tides?.enabled !== false
      const tideHeight = tidesEnabled ? tideSimulator.calculateHeight() : 0

      return {
        windSpeed: state.windSpeed,
        windDirection: state.windDirection,
        depth: state.baseDepth,  // Raw depth - NOT adjusted for tide
        tideHeight: tideHeight,
      }
    },

    /**
     * Get wind speed in knots
     */
    getWindSpeed() {
      return state.windSpeed
    },

    /**
     * Get wind direction in degrees (direction wind comes FROM)
     */
    getWindDirection() {
      return state.windDirection
    },

    /**
     * Get water depth in meters (raw measurement, NOT adjusted for tide)
     */
    getDepth() {
      return state.baseDepth
    },

    /**
     * Get current tide height
     */
    getTideHeight() {
      const tidesEnabled = config.tides?.enabled !== false
      return tidesEnabled ? tideSimulator.calculateHeight() : 0
    },

    /**
     * Get complete tide state for SignalK publishing
     */
    getTideState() {
      return tideSimulator.getTideState()
    },

    /**
     * Get tide simulator for direct access
     */
    getTideSimulator() {
      return tideSimulator
    },

    /**
     * Set wind speed directly
     *
     * @param {number} speed - Wind speed in knots
     */
    setWindSpeed(speed) {
      state.windSpeed = Math.max(0, Math.min(50, speed))  // Clamp 0-50 knots
    },

    /**
     * Set wind direction directly
     *
     * @param {number} direction - Direction in degrees (0-360)
     */
    setWindDirection(direction) {
      state.windDirection = ((direction % 360) + 360) % 360
    },

    /**
     * Set base water depth (without tide)
     *
     * @param {number} depth - Base depth in meters
     */
    setDepth(depth) {
      state.baseDepth = Math.max(0, depth)
    },

    /**
     * Update wind with realistic gusts and shifts
     * Call this on every physics tick for smooth variation
     *
     * Wind behavior:
     * - Gusts: Gradual speed changes with smooth transitions
     * - Oscillation: Small continuous direction swings (causes boat to swing at anchor)
     * - Shifts: Occasional larger direction changes
     */
    updateWind() {
      const now = Date.now()
      const dt = (now - state.lastUpdateTime) / 1000  // seconds since last update
      state.lastUpdateTime = now

      // Clamp dt to prevent huge jumps after pause
      const clampedDt = Math.min(dt, 0.5)

      // === GUSTS: Smooth speed variation ===
      if (config.wind.gustEnabled) {
        const gustMagnitude = config.wind.gustMagnitude || 3

        // Pick new gust target periodically (every 3-8 seconds)
        if ((now - state.lastGustTime) >= (3000 + Math.random() * 5000)) {
          state.gustTarget = (Math.random() - 0.5) * 2 * gustMagnitude
          state.lastGustTime = now
        }

        // Smoothly approach gust target (exponential smoothing)
        const gustSmoothingRate = 0.5  // How fast to approach target (higher = faster)
        state.gustCurrent += (state.gustTarget - state.gustCurrent) * gustSmoothingRate * clampedDt

        // Apply gust to base speed
        state.windSpeed = config.wind.initialSpeed + state.gustCurrent
        state.windSpeed = Math.max(2, Math.min(40, state.windSpeed))  // Clamp 2-40 knots
      }

      // === OSCILLATION: Small continuous direction swings ===
      // This creates natural boat swinging at anchor even without major shifts
      if (config.wind.shiftEnabled) {
        const oscillationMagnitude = config.wind.oscillationMagnitude || 5  // ±5 degrees
        const oscillationPeriod = config.wind.oscillationPeriod || 30000    // 30 second period

        // Update oscillation phase
        state.oscillationPhase += (2 * Math.PI * clampedDt * 1000) / oscillationPeriod

        // Sinusoidal oscillation with some randomness
        state.directionOscillation = Math.sin(state.oscillationPhase) * oscillationMagnitude
        // Add small random noise for more natural feel
        state.directionOscillation += (Math.random() - 0.5) * 2

        // === SHIFTS: Occasional larger direction changes ===
        const shiftInterval = config.wind.shiftInterval || 30000  // 30 seconds default
        if ((now - state.lastShiftTime) >= shiftInterval) {
          const shiftMagnitude = config.wind.shiftMagnitude || 15  // ±15 degrees
          const shift = (Math.random() - 0.5) * 2 * shiftMagnitude

          // Apply shift to the base direction in config
          // This persists until next shift
          config.wind.initialDirection += shift
          config.wind.initialDirection = ((config.wind.initialDirection % 360) + 360) % 360
          state.lastShiftTime = now
        }

        // Combine base direction with oscillation
        state.windDirection = config.wind.initialDirection + state.directionOscillation
        state.windDirection = ((state.windDirection % 360) + 360) % 360
      }
    },

    /**
     * Reset environment to initial config values
     */
    reset() {
      state.windSpeed = config.wind.initialSpeed
      state.windDirection = config.wind.initialDirection
      state.baseDepth = config.environment.depth
      state.lastGustTime = Date.now()
      state.lastShiftTime = Date.now()
      state.lastUpdateTime = Date.now()
      state.gustTarget = 0
      state.gustCurrent = 0
      state.directionOscillation = 0
      state.oscillationPhase = 0
      tideSimulator.reset()
    },

    /**
     * Enable or disable wind gusts
     */
    setGustsEnabled(enabled) {
      updateConfig({ wind: { gustEnabled: enabled } })
    },

    /**
     * Enable or disable wind shifts
     */
    setShiftsEnabled(enabled) {
      updateConfig({ wind: { shiftEnabled: enabled } })
    },

    /**
     * Get SignalK delta for publishing environment data
     *
     * @returns {Array} - Array of SignalK path/value pairs
     */
    getSignalKUpdates() {
      const tidesEnabled = config.tides?.enabled !== false

      const updates = [
        {
          path: 'environment.wind.speedTrue',
          value: state.windSpeed * 0.51444  // Convert knots to m/s
        },
        {
          path: 'environment.wind.directionTrue',
          value: state.windDirection * Math.PI / 180  // Convert degrees to radians
        },
        {
          path: 'environment.depth.belowSurface',
          value: state.baseDepth  // Raw depth - NOT adjusted for tide
        }
      ]

      // Add tide data if enabled
      if (tidesEnabled) {
        const tideState = tideSimulator.getTideState()
        updates.push(
          { path: 'environment.tide.heightNow', value: tideState.heightNow },
          { path: 'environment.tide.heightHigh', value: tideState.heightHigh },
          { path: 'environment.tide.timeHigh', value: tideState.timeHigh },
          { path: 'environment.tide.heightLow', value: tideState.heightLow },
          { path: 'environment.tide.timeLow', value: tideState.timeLow }
        )
      }

      return updates
    }
  }
}

module.exports = {
  createEnvironment
}

/**
 * Tide Simulation Module
 *
 * Simulates semi-diurnal tides using a simple sine wave model.
 * Publishes the same SignalK paths as the signalk-tides plugin:
 *   - environment.tide.heightNow
 *   - environment.tide.heightHigh
 *   - environment.tide.timeHigh
 *   - environment.tide.heightLow
 *   - environment.tide.timeLow
 *
 * Based on Marsh Harbor, Bahamas tide characteristics:
 *   - Semi-diurnal (2 highs, 2 lows per day)
 *   - Mean high: 0.88m, Mean low: 0.16m
 *   - M2 period: 12.42 hours (44712 seconds)
 */

const { config } = require('../config/simulationConfig')

// Default tide configuration (Marsh Harbor, Bahamas)
const DEFAULT_TIDES_CONFIG = {
  M2_PERIOD: 44712,      // 12.42 hours in seconds (M2 lunar semi-diurnal)
  MEAN_HEIGHT: 0.52,     // meters - (0.88 + 0.16) / 2
  AMPLITUDE: 0.36,       // meters - (0.88 - 0.16) / 2
  epochOffset: 0         // Phase offset in seconds (for syncing with real tides)
}

/**
 * Create a tide simulator
 *
 * @param {object} initialConfig - Optional configuration override
 * @returns {object} - Tide simulator with methods
 */
function createTideSimulator(initialConfig = {}) {
  // Merge with config from simulationConfig if available
  const tidesConfig = {
    ...DEFAULT_TIDES_CONFIG,
    ...config.tides,
    ...initialConfig
  }

  // Start time for phase calculation
  let startTime = Date.now() / 1000

  return {
    /**
     * Calculate current tide height
     *
     * @param {number} currentTime - Unix timestamp in seconds (default: now)
     * @returns {number} - Tide height in meters
     */
    calculateHeight(currentTime = Date.now() / 1000) {
      const elapsed = currentTime - startTime + tidesConfig.epochOffset
      const phase = (elapsed % tidesConfig.M2_PERIOD) / tidesConfig.M2_PERIOD
      return tidesConfig.MEAN_HEIGHT +
             tidesConfig.AMPLITUDE * Math.sin(2 * Math.PI * phase)
    },

    /**
     * Get time and height of next high tide
     *
     * @param {number} currentTime - Unix timestamp in seconds (default: now)
     * @returns {object} - { time: ISO string, height: meters }
     */
    getNextHighTide(currentTime = Date.now() / 1000) {
      const elapsed = currentTime - startTime + tidesConfig.epochOffset
      const currentPhase = (elapsed % tidesConfig.M2_PERIOD) / tidesConfig.M2_PERIOD

      // High tide occurs at phase 0.25 (sin peak at π/2)
      const highPhase = 0.25
      let timeToHigh = (highPhase - currentPhase) * tidesConfig.M2_PERIOD
      if (timeToHigh <= 0) timeToHigh += tidesConfig.M2_PERIOD

      return {
        time: new Date((currentTime + timeToHigh) * 1000).toISOString(),
        height: tidesConfig.MEAN_HEIGHT + tidesConfig.AMPLITUDE
      }
    },

    /**
     * Get time and height of next low tide
     *
     * @param {number} currentTime - Unix timestamp in seconds (default: now)
     * @returns {object} - { time: ISO string, height: meters }
     */
    getNextLowTide(currentTime = Date.now() / 1000) {
      const elapsed = currentTime - startTime + tidesConfig.epochOffset
      const currentPhase = (elapsed % tidesConfig.M2_PERIOD) / tidesConfig.M2_PERIOD

      // Low tide occurs at phase 0.75 (sin trough at 3π/2)
      const lowPhase = 0.75
      let timeToLow = (lowPhase - currentPhase) * tidesConfig.M2_PERIOD
      if (timeToLow <= 0) timeToLow += tidesConfig.M2_PERIOD

      return {
        time: new Date((currentTime + timeToLow) * 1000).toISOString(),
        height: tidesConfig.MEAN_HEIGHT - tidesConfig.AMPLITUDE
      }
    },

    /**
     * Get complete tide state for SignalK publishing
     *
     * @param {number} currentTime - Unix timestamp in seconds (default: now)
     * @returns {object} - Full tide state
     */
    getTideState(currentTime = Date.now() / 1000) {
      const nextHigh = this.getNextHighTide(currentTime)
      const nextLow = this.getNextLowTide(currentTime)

      return {
        heightNow: this.calculateHeight(currentTime),
        heightHigh: nextHigh.height,
        timeHigh: nextHigh.time,
        heightLow: nextLow.height,
        timeLow: nextLow.time
      }
    },

    /**
     * Get SignalK delta updates for tide data
     *
     * @returns {Array} - Array of SignalK path/value pairs
     */
    getSignalKUpdates() {
      const state = this.getTideState()
      return [
        { path: 'environment.tide.heightNow', value: state.heightNow },
        { path: 'environment.tide.heightHigh', value: state.heightHigh },
        { path: 'environment.tide.timeHigh', value: state.timeHigh },
        { path: 'environment.tide.heightLow', value: state.heightLow },
        { path: 'environment.tide.timeLow', value: state.timeLow }
      ]
    },

    /**
     * Get current configuration
     */
    getConfig() {
      return { ...tidesConfig }
    },

    /**
     * Reset the start time (for testing or sync)
     */
    reset() {
      startTime = Date.now() / 1000
    },

    /**
     * Set epoch offset for syncing with real tides
     *
     * @param {number} offset - Offset in seconds
     */
    setEpochOffset(offset) {
      tidesConfig.epochOffset = offset
    }
  }
}

module.exports = {
  createTideSimulator,
  DEFAULT_TIDES_CONFIG
}

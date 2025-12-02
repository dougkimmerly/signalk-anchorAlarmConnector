/**
 * Physics Module - Main Export
 *
 * Exports all physics components for use by the simulation orchestrator.
 */

const { createBoat } = require('./boat')
const { createEnvironment } = require('./environment')
const { createIntegrator } = require('./integrator')

// Force modules
const windForce = require('./forces/wind')
const waterDragForce = require('./forces/waterDrag')
const slackConstraintForce = require('./forces/slackConstraint')
const motorForce = require('./forces/motor')

// Config
const simulationConfig = require('../config/simulationConfig')

module.exports = {
  // State creators
  createBoat,
  createEnvironment,
  createIntegrator,

  // Force modules (for direct access if needed)
  forces: {
    wind: windForce,
    waterDrag: waterDragForce,
    slackConstraint: slackConstraintForce,
    motor: motorForce,
  },

  // Motor control (direct access for endpoints)
  motor: motorForce,

  // Config access
  config: simulationConfig,
}

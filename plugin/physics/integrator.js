/**
 * Physics Integrator Module
 *
 * Collects forces from all enabled modules and applies them to the boat.
 * This is the core physics loop that ties everything together.
 *
 * RESPONSIBILITIES:
 * 1. Query each enabled force module
 * 2. Apply forces to boat
 * 3. Apply torques for heading
 * 4. Update boat state
 * 5. Log force contributions for debugging
 */

const { config, isForceEnabled } = require('../config/simulationConfig')
const { calculateWindForce, calculateWeathervvaneTorque, calculateAnchorTorque, calculateAnchoredHeadingTorque } = require('./forces/wind')
const { calculateWaterDrag } = require('./forces/waterDrag')
const { isConstraintActive, calculateTensionRatio, calculateChainWeightForce } = require('./forces/slackConstraint')
const { calculateMotorForce, getMotorState } = require('./forces/motor')

/**
 * Create a physics integrator
 *
 * @param {object} boat - Boat state object (from boat.js)
 * @param {object} environment - Environment state object (from environment.js)
 * @returns {object} - Integrator with step() method
 */
function createIntegrator(boat, environment) {
  let iteration = 0
  let lastLogTime = Date.now()

  // Store last calculated forces for logging/debugging
  const lastForces = {
    wind: { forceX: 0, forceY: 0, magnitude: 0 },
    waterDrag: { forceX: 0, forceY: 0, magnitude: 0 },
    motor: { forceX: 0, forceY: 0, magnitude: 0 },
    chainWeight: { forceX: 0, forceY: 0, magnitude: 0, suspendedLength: 0 },
    constraint: { forceX: 0, forceY: 0, magnitude: 0 },
    total: { forceX: 0, forceY: 0, magnitude: 0 },
    torque: { wind: 0, anchor: 0, total: 0 },
  }

  return {
    /**
     * Perform one physics integration step
     *
     * @param {object} externalState - External state from SignalK (e.g., rodeDeployed)
     * @returns {object} - Updated state for publishing
     */
    step(externalState = {}) {
      iteration++
      const boatState = boat.getState()
      const envState = environment.getState()

      // Reset force accumulators
      let totalForceX = 0
      let totalForceY = 0
      let totalTorque = 0

      // ============================================
      // WIND FORCE
      // ============================================
      if (isForceEnabled('wind')) {
        const windForce = calculateWindForce(
          envState.windSpeed,
          envState.windDirection,
          boatState.heading
        )

        totalForceX += windForce.forceX
        totalForceY += windForce.forceY

        lastForces.wind = {
          forceX: windForce.forceX,
          forceY: windForce.forceY,
          magnitude: windForce.forceMagnitude,
          pushDirection: windForce.pushDirection,
        }

        // Heading torque from wind (weathervane effect)
        if (!boatState.isAnchored) {
          const weathervaneTorque = calculateWeathervvaneTorque(
            envState.windDirection,
            boatState.heading,
            envState.windSpeed
          )
          totalTorque += weathervaneTorque
          lastForces.torque.wind = weathervaneTorque
        }
      }

      // ============================================
      // WATER DRAG FORCE (directional based on heading)
      // ============================================
      if (isForceEnabled('waterDrag')) {
        const dragForce = calculateWaterDrag(
          boatState.velocityX,
          boatState.velocityY,
          boatState.heading  // Pass heading for directional drag
        )

        totalForceX += dragForce.forceX
        totalForceY += dragForce.forceY

        lastForces.waterDrag = {
          forceX: dragForce.forceX,
          forceY: dragForce.forceY,
          magnitude: Math.sqrt(dragForce.forceX ** 2 + dragForce.forceY ** 2),
          coefficient: dragForce.coefficient,  // Log which coefficient was used
        }
      }

      // ============================================
      // HEADING TORQUE (anchored vs free)
      // ============================================
      if (boatState.isAnchored && isForceEnabled('wind')) {
        // When anchored: Combined anchor pull + wind influence
        const bearingToAnchor = boat.getBearingToAnchor()
        const distanceToAnchor = boat.getDistanceToAnchor()
        const rodeDeployed = externalState.rodeDeployed || 0

        if (bearingToAnchor !== null) {
          const headingTorques = calculateAnchoredHeadingTorque(
            bearingToAnchor,
            envState.windDirection,
            boatState.heading,
            envState.windSpeed,
            distanceToAnchor,
            rodeDeployed
          )

          totalTorque += headingTorques.totalTorque
          lastForces.torque.anchor = headingTorques.anchorTorque
          lastForces.torque.wind = headingTorques.windTorque
          lastForces.torque.tensionFactor = headingTorques.tensionFactor
        }
      } else if (boatState.isAnchored) {
        // Anchored but wind disabled: just anchor torque
        const bearingToAnchor = boat.getBearingToAnchor()
        if (bearingToAnchor !== null) {
          const anchorTorque = calculateAnchorTorque(
            bearingToAnchor,
            boatState.heading
          )
          totalTorque += anchorTorque
          lastForces.torque.anchor = anchorTorque
        }
      }

      // ============================================
      // MOTOR FORCE (Phase 4)
      // Thrust along/opposite heading for deployment/retrieval
      // During retrieval: steer toward anchor (not just along heading)
      // Stop motor when within 3m of anchor AND rode nearly retrieved
      // Velocity-based throttle reduction to prevent overshoot
      // ============================================
      if (isForceEnabled('motor')) {
        const bearingToAnchor = boat.getBearingToAnchor()
        const distanceToAnchor = boat.getDistanceToAnchor()
        const boatSpeed = Math.sqrt(boatState.velocityX ** 2 + boatState.velocityY ** 2)
        const rodeDeployed = externalState.rodeDeployed || 0

        const motorForce = calculateMotorForce(
          boatState.heading,
          bearingToAnchor,      // For retrieval: steer toward anchor
          distanceToAnchor,     // Stop when close to anchor
          boatSpeed,            // Velocity-based throttle reduction
          rodeDeployed          // Only stop if rode nearly retrieved
        )

        totalForceX += motorForce.forceX
        totalForceY += motorForce.forceY

        lastForces.motor = {
          forceX: motorForce.forceX,
          forceY: motorForce.forceY,
          magnitude: motorForce.magnitude,
          direction: motorForce.direction,
          throttle: motorForce.throttle,
          reason: motorForce.reason,  // e.g., 'close_to_anchor'
        }
      } else {
        lastForces.motor = { forceX: 0, forceY: 0, magnitude: 0, direction: 'stop', throttle: 0 }
      }

      // ============================================
      // SLACK CONSTRAINT (Phase 3)
      // Chain controller publishes slack to SignalK
      // Two components:
      // 1. Chain weight force (catenary) - pulls boat toward anchor
      // 2. Velocity constraint (dead stop) - prevents moving away from anchor
      //
      // BEHAVIOR BY MODE:
      // - DEPLOYMENT: Disable chain weight force so boat drifts away with wind
      // - RETRIEVAL: Chain weight force ACTIVE - this naturally pulls boat
      //   toward anchor as windlass takes up slack. Motor only if needed.
      // - IDLE: Both active for normal anchored behavior
      // ============================================
      if (isForceEnabled('slackConstraint') && boatState.isAnchored) {
        const bearingToAnchor = boat.getBearingToAnchor()
        const slack = externalState.slack  // From chain controller via SignalK
        const depth = externalState.depth || envState.depth || config.environment.depth

        // Check if actively deploying chain (boat should drift freely)
        // IMPORTANT: Use command as primary indicator, chainDirection only shows
        // 'down'/'up' when chain is moving - it goes to 'idle' during pauses
        const isDeploying = externalState.command === 'autoDrop' ||
                           externalState.chainDirection === 'down'

        if (bearingToAnchor !== null && slack !== undefined) {
          // 1. CHAIN WEIGHT FORCE (catenary effect)
          // Applied as a normal force - pulls boat toward anchor based on
          // how much chain is suspended (lifted off seabed)
          // DISABLED during deployment - boat needs to drift away with wind
          // ENABLED during retrieval - this is how boat naturally moves forward
          if (!isDeploying) {
            const chainForce = calculateChainWeightForce(slack, depth, bearingToAnchor)
            totalForceX += chainForce.forceX
            totalForceY += chainForce.forceY

            lastForces.chainWeight = {
              forceX: chainForce.forceX,
              forceY: chainForce.forceY,
              magnitude: chainForce.magnitude,
              suspendedLength: chainForce.suspendedLength,
            }
          } else {
            // Deploying - no chain weight force (let wind push boat away)
            lastForces.chainWeight = { forceX: 0, forceY: 0, magnitude: 0, suspendedLength: 0, disabled: 'deploying' }
          }

          // 2. VELOCITY CONSTRAINT (dead stop)
          // Activate when slack <= buffer (approaching taut)
          // Buffer prevents overshoot - constraint activates slightly before fully taut
          // This zeros the velocity component moving away from anchor
          //
          // During DEPLOYMENT: Only apply constraint when slack < 0 (rode fully extended)
          //   - Boat can drift freely while there's slack (chain weight force disabled)
          //   - But boat CANNOT drift past the rode length (physically impossible)
          // During RETRIEVAL/IDLE: Apply constraint when slack <= buffer (normal behavior)
          const isConstrained = isDeploying
            ? (slack < 0)  // During deployment: hard stop only when rode fully extended
            : isConstraintActive(slack)  // Normal: activate at buffer threshold
          boat.setVelocityConstraint(isConstrained, bearingToAnchor)

          // Calculate tension ratio for logging
          const tensionRatio = slack >= depth ? 0 : (depth - slack) / depth

          lastForces.constraint = {
            forceX: 0,  // Velocity constraint doesn't apply force
            forceY: 0,
            magnitude: 0,
            isConstrained: isConstrained,
            tensionRatio: tensionRatio,
            slack: slack,
            mode: 'velocity_constraint',
          }
        } else {
          // No constraint data - disable velocity constraint and zero chain weight
          boat.setVelocityConstraint(false)
          lastForces.chainWeight = { forceX: 0, forceY: 0, magnitude: 0, suspendedLength: 0 }
        }
      } else {
        // Constraint disabled or not anchored - disable velocity constraint
        boat.setVelocityConstraint(false)
        lastForces.chainWeight = { forceX: 0, forceY: 0, magnitude: 0, suspendedLength: 0 }
      }

      // ============================================
      // APPLY FORCES TO BOAT
      // ============================================
      boat.applyForce(totalForceX, totalForceY)
      boat.applyTorque(totalTorque)

      // Store totals
      lastForces.total = {
        forceX: totalForceX,
        forceY: totalForceY,
        magnitude: Math.sqrt(totalForceX ** 2 + totalForceY ** 2),
      }
      lastForces.torque.total = totalTorque

      // ============================================
      // UPDATE BOAT STATE
      // ============================================
      const changes = boat.update()

      // ============================================
      // LOGGING
      // ============================================
      if (config.logging.enabled && config.logging.logForces) {
        if (iteration % config.logging.logInterval === 0) {
          this.logState(boatState, envState, changes)
        }
      }

      // Return updated state
      return {
        ...boat.getState(),
        forces: this.getLastForces(),
        environment: envState,
        iteration,
      }
    },

    /**
     * Get last calculated forces (for debugging/logging)
     */
    getLastForces() {
      return JSON.parse(JSON.stringify(lastForces))
    },

    /**
     * Log current state (for debugging)
     */
    logState(boatState, envState, changes) {
      const speed = Math.sqrt(boatState.velocityX ** 2 + boatState.velocityY ** 2)
      const windMs = envState.windSpeed * 0.51444

      console.log(`\n=== Physics Step ${iteration} ===`)
      console.log(`Wind: ${envState.windSpeed.toFixed(1)} kn from ${envState.windDirection}°`)
      console.log(`Position: ${boatState.latitude.toFixed(6)}, ${boatState.longitude.toFixed(6)}`)
      console.log(`Velocity: (${boatState.velocityX.toFixed(3)}, ${boatState.velocityY.toFixed(3)}) m/s = ${speed.toFixed(3)} m/s`)
      console.log(`Heading: ${boatState.heading.toFixed(1)}°`)

      if (config.logging.logForces) {
        console.log(`Forces:`)
        console.log(`  Wind: (${lastForces.wind.forceX.toFixed(1)}, ${lastForces.wind.forceY.toFixed(1)}) N = ${lastForces.wind.magnitude.toFixed(1)} N`)
        console.log(`  Drag: (${lastForces.waterDrag.forceX.toFixed(1)}, ${lastForces.waterDrag.forceY.toFixed(1)}) N [coeff=${lastForces.waterDrag.coefficient?.toFixed(0) || 'N/A'}]`)
        console.log(`  Total: (${lastForces.total.forceX.toFixed(1)}, ${lastForces.total.forceY.toFixed(1)}) N`)
        console.log(`  Accel: (${changes.accelX.toFixed(4)}, ${changes.accelY.toFixed(4)}) m/s²`)

        // Terminal velocity logging (using current directional coefficient)
        if (lastForces.wind.magnitude > 0 && lastForces.waterDrag.coefficient) {
          const terminalVelocity = Math.sqrt(lastForces.wind.magnitude / lastForces.waterDrag.coefficient)
          const percentOfTerminal = (speed / terminalVelocity) * 100
          console.log(`  Terminal: ${terminalVelocity.toFixed(2)} m/s (currently at ${percentOfTerminal.toFixed(0)}%)`)
        }
      }

      if (boatState.isAnchored) {
        const distance = boat.getDistanceToAnchor()
        console.log(`Anchored: ${distance?.toFixed(1)}m to anchor`)
      }
    },

    /**
     * Get iteration count
     */
    getIteration() {
      return iteration
    },

    /**
     * Reset iteration counter
     */
    reset() {
      iteration = 0
      lastLogTime = Date.now()
    },
  }
}

module.exports = {
  createIntegrator
}

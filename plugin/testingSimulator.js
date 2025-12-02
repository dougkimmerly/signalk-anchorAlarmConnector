/**
 * Test Simulation V2 - Modular Physics-Based Anchor Simulation
 *
 * This is the new modular simulation that uses isolated physics modules.
 * It replaces the monolithic testSimulation.js with a cleaner architecture.
 *
 * CRITICAL BOUNDARIES:
 * - Simulator CREATES: wind, depth, boat position, heading, speed
 * - Simulator READS ONLY from SignalK (these are EXTERNAL, never calculated here):
 *   - navigation.anchor.position (from anchor alarm plugin)
 *   - navigation.anchor.rodeDeployed (from chain controller)
 *   - navigation.anchor.chainSlack (from chain controller)
 * - Simulator NEVER modifies: anchor position, rode deployed, slack, chain direction
 *
 * The chain controller (ESP32) and anchor alarm plugin are COMPLETELY INDEPENDENT.
 */

const { createBoat, createEnvironment, createIntegrator, config, motor } = require('./physics')
const { isForceEnabled, setForceEnabled, updateConfig, getConfig } = config
const { setMotorDirection, setMotorThrottle, getMotorState, isManualMode } = motor

// Module state
let boat = null
let environment = null
let integrator = null
let physicsInterval = null
let windInterval = null
let app = null
let sendChangeCallback = null

// Logging
let testDataLog = []
let loggingEnabled = false
let testStartTime = null

/**
 * Start the V2 simulation
 *
 * @param {object} signalkApp - SignalK app object
 * @param {function} sendChange - Function to send SignalK updates
 * @param {object} options - Configuration options
 */
function runTestSequence(signalkApp, sendChange, options = {}) {
  console.log('\n========================================')
  console.log('  SIMULATION V2 - Starting')
  console.log('  Using modular physics engine')
  console.log('========================================\n')

  app = signalkApp
  sendChangeCallback = sendChange

  // Initialize logging
  loggingEnabled = options.enableLogging || false
  if (loggingEnabled) {
    testDataLog = []
    testStartTime = Date.now()
    console.log('Data logging enabled')
  }

  // Apply any config overrides from options
  if (options.config) {
    updateConfig(options.config)
  }

  // Create physics objects
  boat = createBoat()
  environment = createEnvironment()
  integrator = createIntegrator(boat, environment)

  // Log initial configuration
  const cfg = getConfig()
  console.log('Configuration:')
  console.log(`  Forces enabled: wind=${isForceEnabled('wind')}, waterDrag=${isForceEnabled('waterDrag')}, motor=${isForceEnabled('motor')}, slackConstraint=${isForceEnabled('slackConstraint')}`)
  console.log(`  Wind: ${cfg.wind.initialSpeed} kn from ${cfg.wind.initialDirection}°`)
  console.log(`  Boat mass: ${cfg.physics.boatMass} kg`)
  console.log(`  Water drag coefficient: ${cfg.waterDrag.coefficient}`)

  // Set initial position in SignalK
  const initialState = boat.getState()
  sendChange('navigation.position', {
    latitude: initialState.latitude,
    longitude: initialState.longitude,
  })
  sendChange('environment.depth.belowSurface', cfg.environment.depth)

  // Set initial heading
  sendChange('navigation.headingTrue', initialState.heading * Math.PI / 180)

  // Set initial wind
  const envState = environment.getState()
  sendChange('environment.wind.speedTrue', envState.windSpeed * 0.51444)
  sendChange('environment.wind.directionTrue', envState.windDirection * Math.PI / 180)

  console.log(`Initial position: ${initialState.latitude.toFixed(6)}, ${initialState.longitude.toFixed(6)}`)
  console.log(`Initial heading: ${initialState.heading}°`)

  // Start wind variation interval (if enabled)
  // Update every second for smooth oscillation and gust transitions
  if (cfg.wind.gustEnabled || cfg.wind.shiftEnabled) {
    windInterval = setInterval(() => {
      environment.updateWind()
      const newEnv = environment.getState()
      sendChange('environment.wind.speedTrue', newEnv.windSpeed * 0.51444)
      sendChange('environment.wind.directionTrue', newEnv.windDirection * Math.PI / 180)
    }, 1000)  // Update every second for smooth variation
  }

  // Start physics loop
  const dt = cfg.physics.dt
  const intervalMs = dt * 1000

  physicsInterval = setInterval(() => {
    runPhysicsStep()
  }, intervalMs)

  console.log(`Physics loop started at ${1/dt} Hz (${intervalMs}ms intervals)`)
  console.log('========================================\n')
}

/**
 * Run a single physics step
 */
function runPhysicsStep() {
  if (!boat || !environment || !integrator) return

  // Read external state from SignalK
  const externalState = readExternalState()

  // Update anchor state if available
  if (externalState.anchorPosition) {
    boat.setAnchor(
      externalState.anchorPosition.latitude,
      externalState.anchorPosition.longitude
    )
  }

  // Run physics integration
  const state = integrator.step(externalState)

  // Automatic motor control based on chain direction and speed
  updateAutoMotor(state, externalState)

  // Publish updated state to SignalK
  publishState(state)

  // Log data if enabled
  if (loggingEnabled) {
    logTestData(state, externalState)
  }
}

/**
 * Read external state from SignalK (chain controller data)
 */
function readExternalState() {
  if (!app) return {}

  const state = {}

  // Read rode deployed (from chain controller)
  try {
    const rodePath = 'navigation.anchor.rodeDeployed'
    const rodeValue = app.getSelfPath(rodePath)
    if (rodeValue !== undefined && rodeValue !== null) {
      state.rodeDeployed = typeof rodeValue === 'object' ? rodeValue.value : rodeValue
    }
  } catch (e) {
    // Ignore read errors
  }

  // Read anchor position (set by anchor alarm plugin)
  try {
    const anchorPath = 'navigation.anchor.position'
    const anchorValue = app.getSelfPath(anchorPath)
    if (anchorValue && anchorValue.value) {
      state.anchorPosition = anchorValue.value
    } else if (anchorValue && anchorValue.latitude) {
      state.anchorPosition = anchorValue
    }
  } catch (e) {
    // Ignore read errors
  }

  // Read slack from chain controller (published to SignalK)
  // CRITICAL: Slack is calculated by the chain controller, NOT the simulator
  try {
    const slackPath = 'navigation.anchor.chainSlack'
    const slackValue = app.getSelfPath(slackPath)
    if (slackValue !== undefined && slackValue !== null) {
      state.slack = typeof slackValue === 'object' ? slackValue.value : slackValue
    }
  } catch (e) {
    // Ignore read errors - slack comes from chain controller
  }

  // Read depth for constraint calculations
  try {
    const depthPath = 'environment.depth.belowSurface'
    const depthValue = app.getSelfPath(depthPath)
    if (depthValue !== undefined && depthValue !== null) {
      state.depth = typeof depthValue === 'object' ? depthValue.value : depthValue
    }
  } catch (e) {
    // Use default depth from config
    state.depth = config.environment.depth
  }

  // If depth wasn't set by above, use config default
  if (state.depth === undefined) {
    state.depth = config.environment.depth
  }

  // Read chain direction (from chain controller)
  // 'down' = deploying, 'up' = retrieving, other = idle
  try {
    const chainDirPath = 'navigation.anchor.chainDirection'
    const chainDirValue = app.getSelfPath(chainDirPath)
    if (chainDirValue !== undefined && chainDirValue !== null) {
      state.chainDirection = typeof chainDirValue === 'object' ? chainDirValue.value : chainDirValue
    }
  } catch (e) {
    // Ignore read errors
  }

  return state
}

/**
 * Automatic motor control based on chain direction and boat speed
 *
 * DEPLOYMENT (chainDirection='down'):
 * - If boat speed is too slow, engage motorBackward to help move away from anchor
 * - Target speed ~0.5 m/s (~1kn) to allow chain to pay out
 *
 * RETRIEVAL (chainDirection='up'):
 * - Engage motorForward to create slack for chain lifting
 * - Need slack in chain so windlass can lift it
 *
 * IDLE (no chain movement):
 * - Stop motor to save energy
 */
function updateAutoMotor(boatState, externalState) {
  const cfg = getConfig()

  // Check if auto-motor is enabled
  if (!cfg.motor?.autoMotorEnabled) {
    return
  }

  // Don't override manual motor control
  if (isManualMode()) {
    return
  }

  const chainDirection = externalState.chainDirection
  const boatSpeed = boatState.speed || 0
  const slack = externalState.slack

  // Get thresholds from config
  const deployMinSpeed = cfg.motor?.deployMinSpeed ?? 0.2
  const deployTargetSpeed = cfg.motor?.deployTargetSpeed ?? 0.5
  const retrieveSlackTarget = cfg.motor?.retrieveSlackTarget ?? 1.0

  const currentMotorState = getMotorState()

  if (chainDirection === 'down') {
    // DEPLOYMENT: Need boat to move away from anchor
    // If wind isn't moving boat fast enough, engage motorBackward

    if (boatSpeed < deployMinSpeed) {
      // Too slow - engage motor backward at full throttle
      if (currentMotorState.direction !== 'backward' || currentMotorState.throttle < 1.0) {
        setForceEnabled('motor', true)
        setMotorDirection('backward')
        setMotorThrottle(1.0)
        console.log(`[AUTO-MOTOR] Deployment assist: speed ${boatSpeed.toFixed(2)} m/s < ${deployMinSpeed} m/s, engaging motorBackward`)
      }
    } else if (boatSpeed > deployTargetSpeed * 1.2) {
      // Moving fast enough - reduce or stop motor
      if (currentMotorState.direction === 'backward') {
        setMotorDirection('stop')
        setMotorThrottle(0)
        setForceEnabled('motor', false)
        console.log(`[AUTO-MOTOR] Deployment: speed ${boatSpeed.toFixed(2)} m/s sufficient, stopping motor`)
      }
    }

  } else if (chainDirection === 'up') {
    // RETRIEVAL: Need slack in chain for lifting
    // Engage motorForward to move toward anchor and create slack

    if (slack !== undefined && slack < retrieveSlackTarget) {
      // Not enough slack - engage motor forward
      if (currentMotorState.direction !== 'forward' || currentMotorState.throttle < 1.0) {
        setForceEnabled('motor', true)
        setMotorDirection('forward')
        setMotorThrottle(1.0)
        console.log(`[AUTO-MOTOR] Retrieval assist: slack ${slack.toFixed(2)}m < ${retrieveSlackTarget}m, engaging motorForward`)
      }
    } else if (slack !== undefined && slack > retrieveSlackTarget * 1.5) {
      // Enough slack - stop motor
      if (currentMotorState.direction === 'forward') {
        setMotorDirection('stop')
        setMotorThrottle(0)
        setForceEnabled('motor', false)
        console.log(`[AUTO-MOTOR] Retrieval: slack ${slack.toFixed(2)}m sufficient, stopping motor`)
      }
    }

  } else {
    // IDLE: No chain movement - stop motor if it was auto-engaged
    // Only stop if motor is running (don't interfere with manual control)
    // We track this by checking if motor is enabled but we're not deploying/retrieving
    if (currentMotorState.direction !== 'stop' && isForceEnabled('motor')) {
      // Motor is running but chain is idle - likely auto-engaged, so stop it
      setMotorDirection('stop')
      setMotorThrottle(0)
      setForceEnabled('motor', false)
      console.log(`[AUTO-MOTOR] Chain idle, stopping motor`)
    }
  }
}

/**
 * Publish updated state to SignalK
 */
function publishState(state) {
  if (!sendChangeCallback) return

  // Position
  sendChangeCallback('navigation.position', {
    latitude: state.latitude,
    longitude: state.longitude,
  })

  // Speed over ground
  sendChangeCallback('navigation.speedOverGround', state.speed)

  // Heading
  sendChangeCallback('navigation.headingTrue', state.heading * Math.PI / 180)

  // Environment (wind, depth, tides)
  const envState = environment.getState()
  sendChangeCallback('environment.wind.speedTrue', envState.windSpeed * 0.51444)
  sendChangeCallback('environment.wind.directionTrue', envState.windDirection * Math.PI / 180)
  sendChangeCallback('environment.depth.belowSurface', envState.depth)

  // Publish tide data (if enabled)
  const tideState = environment.getTideState()
  if (tideState) {
    sendChangeCallback('environment.tide.heightNow', tideState.heightNow)
    sendChangeCallback('environment.tide.heightHigh', tideState.heightHigh)
    sendChangeCallback('environment.tide.timeHigh', tideState.timeHigh)
    sendChangeCallback('environment.tide.heightLow', tideState.heightLow)
    sendChangeCallback('environment.tide.timeLow', tideState.timeLow)
  }

  // Motor state - publish separate paths for SKipper app PUT control
  const motorState = getMotorState()

  // Publish state (forward/backward/stop) - this path accepts PUT commands
  sendChangeCallback('navigation.anchor.motor.state', motorState.direction)

  // Publish throttle (1-100 integer percentage) - this path accepts PUT commands
  const throttlePercent = Math.round(motorState.throttle * 100)
  sendChangeCallback('navigation.anchor.motor.throttle', throttlePercent)

  // Also publish combined description for display
  let motorDescription = 'Stopped'
  if (motorState.direction !== 'stop' && motorState.throttle > 0) {
    const dirLabel = motorState.direction === 'forward' ? 'Forward' : 'Backward'
    motorDescription = throttlePercent === 100
      ? `${dirLabel} full thrust`
      : `${dirLabel} ${throttlePercent}%`
  }
  sendChangeCallback('navigation.anchor.motor', motorDescription)
}

/**
 * Log test data for analysis
 */
function logTestData(state, externalState) {
  const elapsed = (Date.now() - testStartTime) / 1000

  testDataLog.push({
    time_sec: elapsed,
    latitude: state.latitude,
    longitude: state.longitude,
    boat_speed: state.speed,
    boat_heading: state.heading,
    velocityX: state.velocityX,
    velocityY: state.velocityY,
    rode_deployed: externalState.rodeDeployed || 0,
    distance: state.isAnchored ? boat.getDistanceToAnchor() : null,
    wind_speed: state.environment.windSpeed,
    wind_direction: state.environment.windDirection,
    forces: state.forces,
  })
}

/**
 * Stop the simulation
 */
function stopTestSimulation() {
  console.log('Stopping V2 simulation...')

  if (physicsInterval) {
    clearInterval(physicsInterval)
    physicsInterval = null
  }

  if (windInterval) {
    clearInterval(windInterval)
    windInterval = null
  }

  // Reset state
  if (boat) boat.reset()
  if (environment) environment.reset()
  if (integrator) integrator.reset()

  console.log('V2 simulation stopped')
}

/**
 * Set boat position directly (for zone testing)
 */
function setBoatPosition(latitude, longitude) {
  if (!boat) return 'Simulation not running'

  boat.setPosition(latitude, longitude)
  boat.setVelocity(0, 0)  // Reset velocity on manual move

  if (sendChangeCallback) {
    sendChangeCallback('navigation.position', { latitude, longitude })
  }

  return `Position set to ${latitude}, ${longitude}`
}

/**
 * Move to alarm zone (for testing)
 */
function moveToZone(signalkApp, zoneName) {
  if (!boat) return 'Simulation not running'

  // Read zone configuration
  const zones = signalkApp.getSelfPath('navigation.anchor.meta.zones')
  if (!zones || !zones.value) {
    return 'No alarm zones configured'
  }

  const anchorPos = signalkApp.getSelfPath('navigation.anchor.position')
  if (!anchorPos || !anchorPos.value) {
    return 'No anchor position set'
  }

  // Find target zone
  const zoneList = zones.value
  let targetDistance = 0

  if (zoneName === 'warn' || zoneName === 'warning') {
    const warnZone = zoneList.find(z => z.state === 'warn')
    if (warnZone) {
      targetDistance = (warnZone.lower + warnZone.upper) / 2
    }
  } else if (zoneName === 'alarm' || zoneName === 'emergency') {
    const alarmZone = zoneList.find(z => z.state === 'alarm')
    if (alarmZone) {
      targetDistance = alarmZone.lower + 1  // Just past threshold
    }
  }

  if (targetDistance === 0) {
    return `Zone '${zoneName}' not found`
  }

  // Calculate new position at target distance from anchor
  const anchorLat = anchorPos.value.latitude
  const anchorLon = anchorPos.value.longitude
  const currentState = boat.getState()

  // Calculate bearing from anchor to current position
  const deltaLat = currentState.latitude - anchorLat
  const deltaLon = currentState.longitude - anchorLon
  const bearing = Math.atan2(deltaLon, deltaLat)

  // Calculate new position
  const cfg = getConfig()
  const newLat = anchorLat + (targetDistance * cfg.physics.metersToLat) * Math.cos(bearing)
  const newLon = anchorLon + (targetDistance * cfg.physics.metersToLon) * Math.sin(bearing)

  setBoatPosition(newLat, newLon)

  return `Moved to ${zoneName} zone (${targetDistance.toFixed(1)}m from anchor)`
}

/**
 * Start motoring forward (toward anchor)
 * Used during retrieval to create slack for chain lifting
 */
function startMotoring(signalkApp) {
  setForceEnabled('motor', true)
  setMotorDirection('forward')
  setMotorThrottle(1.0)
  const state = getMotorState()
  return `Motor forward: direction=${state.direction}, throttle=${state.throttle}`
}

/**
 * Start motoring backward (away from anchor)
 * Used during deployment when wind is insufficient
 */
function startMotoringBackwards(signalkApp) {
  setForceEnabled('motor', true)
  setMotorDirection('backward')
  setMotorThrottle(1.0)
  const state = getMotorState()
  return `Motor backward: direction=${state.direction}, throttle=${state.throttle}`
}

/**
 * Stop motoring
 */
function stopMotoring() {
  setMotorDirection('stop')
  setMotorThrottle(0)
  setForceEnabled('motor', false)
  return 'Motor stopped'
}

/**
 * Set motor throttle (0.0 to 1.0)
 */
function setMotorPower(throttle) {
  setMotorThrottle(throttle)
  const state = getMotorState()
  return `Motor throttle set to ${state.throttle}`
}

/**
 * Get collected test data
 */
function getTestData() {
  return testDataLog
}

/**
 * Clear test data
 */
function clearTestData() {
  testDataLog = []
  testStartTime = Date.now()
}

/**
 * Get current simulation state (for debugging)
 */
function getSimulationState() {
  if (!boat || !environment || !integrator) {
    return { running: false }
  }

  return {
    running: true,
    boat: boat.getState(),
    environment: environment.getState(),
    forces: integrator.getLastForces(),
    config: getConfig(),
    iteration: integrator.getIteration(),
  }
}

/**
 * Update simulation configuration at runtime
 */
function updateSimulationConfig(updates) {
  updateConfig(updates)
  return getConfig()
}

/**
 * Reset simulation to initial state
 */
function resetSimulation() {
  if (boat) boat.reset()
  if (environment) environment.reset()
  if (integrator) integrator.reset()

  clearTestData()

  // Publish reset position
  if (sendChangeCallback && boat) {
    const state = boat.getState()
    sendChangeCallback('navigation.position', {
      latitude: state.latitude,
      longitude: state.longitude,
    })
  }

  return 'Simulation reset to initial state'
}

/**
 * Move boat south by specified distance (for testing)
 * @param {number} distance - Distance in meters
 */
function moveSouth(distance) {
  if (!app) return 'App not initialized'

  let position = app.getSelfPath('navigation.position')?.value
  if (position) {
    // Approximately 0.000009 degrees latitude per meter
    position.latitude -= distance * config.getConfig().physics.metersToLat
    if (sendChangeCallback) {
      sendChangeCallback('navigation.position', position)
    }
    console.log(`Moved south by ${distance} meters`)
    return `Moved south by ${distance} meters`
  } else {
    console.log('Unable to move: current position unknown')
    return 'Unable to move: current position unknown'
  }
}

/**
 * Register test router endpoints
 * These are only for testing and should not be in production
 * @param {object} router - Express router from SignalK
 */
function registerTestRouterEndpoints(router) {
  const testSimulation = module.exports  // Reference to exported functions

  router.put('/movesouth', (req, res) => {
    const distance = req.body.distance || 5
    const result = moveSouth(distance)
    res.send(result)
  })

  router.put('/movetowarning', (req, res) => {
    const result = testSimulation.moveToZone(app, 'warn')
    res.send(result)
  })

  router.put('/movetoalarm', (req, res) => {
    const result = testSimulation.moveToZone(app, 'alarm')
    res.send(result)
  })

  router.put('/motorforward', (req, res) => {
    const result = testSimulation.startMotoring(app)
    res.send(result)
  })

  router.put('/motorstop', (req, res) => {
    const result = testSimulation.stopMotoring()
    res.send(result)
  })

  router.put('/motorbackward', (req, res) => {
    const result = testSimulation.startMotoringBackwards(app)
    res.send(result)
  })

  router.put('/motorthrottle', (req, res) => {
    const throttle = parseFloat(req.body.throttle)
    if (isNaN(throttle) || throttle < 0 || throttle > 1) {
      return res.status(400).send('Throttle must be a number between 0.0 and 1.0')
    }
    const result = testSimulation.setMotorPower(throttle)
    res.send(result)
  })

  // Simulation endpoints
  router.get('/simulation/state', (req, res) => {
    res.json(testSimulation.getSimulationState())
  })

  router.put('/simulation/config', (req, res) => {
    const newConfig = testSimulation.updateSimulationConfig(req.body)
    res.json(newConfig)
  })

  router.put('/simulation/reset', (req, res) => {
    const result = testSimulation.resetSimulation()
    res.send(result)
  })

  console.log('Test router endpoints registered:')
  console.log('  - PUT /movesouth, /movetowarning, /movetoalarm')
  console.log('  - PUT /motorforward, /motorstop, /motorbackward, /motorthrottle')
  console.log('  - GET /simulation/state')
  console.log('  - PUT /simulation/config, /simulation/reset')
}

/**
 * Register motor PUT handlers for SignalK paths
 * These are only for testing via SignalK PUT API
 * @param {object} signalkApp - SignalK app object
 * @param {string} pluginId - Plugin ID for delta messages
 */
function registerMotorPutHandlers(signalkApp, pluginId) {
  const { setManualMode } = motor

  // Helper to publish motor state back to SignalK
  function publishMotorState() {
    const motorState = getMotorState()
    const throttlePercent = Math.round(motorState.throttle * 100)

    console.log(`[PUT] Publishing motor state: ${motorState.direction}, throttle: ${throttlePercent}%`)

    const delta = {
      context: 'vessels.self',
      updates: [
        {
          timestamp: new Date().toISOString(),
          values: [
            {
              path: 'navigation.anchor.motor.state',
              value: motorState.direction
            },
            {
              path: 'navigation.anchor.motor.throttle',
              value: throttlePercent
            }
          ]
        }
      ]
    }
    signalkApp.handleMessage(pluginId, delta)
    console.log(`[PUT] Delta sent: ${JSON.stringify(delta.updates[0].values)}`)
  }

  // PUT handler for motor state (forward/backward/stop)
  signalkApp.registerPutHandler(
    'vessels.self',
    'navigation.anchor.motor.state',
    (context, path, value) => {
      const newState = typeof value === 'object' ? value.value : value

      console.log(`[PUT] Motor state request: ${newState}`)

      const validStates = ['forward', 'backward', 'stop']
      if (!validStates.includes(newState)) {
        console.log(`[PUT] Invalid motor state: ${newState}`)
        return { state: 'COMPLETED', statusCode: 400, message: `Invalid state '${newState}'. Must be one of: ${validStates.join(', ')}` }
      }

      try {
        setManualMode(true)
        const currentState = getMotorState()

        if (newState === 'stop') {
          setMotorDirection('stop')
          setForceEnabled('motor', false)
          console.log(`[PUT] Motor stopped (manual mode enabled)`)
        } else {
          if (currentState.direction === 'stop' || currentState.throttle === 0) {
            setMotorThrottle(0.05)
            console.log(`[PUT] Motor ${newState} started at 5% throttle (default, manual mode enabled)`)
          } else {
            console.log(`[PUT] Motor ${newState} at ${Math.round(currentState.throttle * 100)}% throttle (manual mode enabled)`)
          }
          setMotorDirection(newState)
          setForceEnabled('motor', true)
        }

        publishMotorState()
        return { state: 'COMPLETED', statusCode: 200 }
      } catch (error) {
        console.error(`[PUT] Motor state error:`, error)
        return { state: 'COMPLETED', statusCode: 500, message: error.message }
      }
    }
  )

  // PUT handler for motor throttle (1-100 percentage)
  signalkApp.registerPutHandler(
    'vessels.self',
    'navigation.anchor.motor.throttle',
    (context, path, value) => {
      const throttle = typeof value === 'object' ? value.value : value
      const throttleInt = parseInt(throttle, 10)

      console.log(`[PUT] Motor throttle request: ${throttle}`)

      if (isNaN(throttleInt) || throttleInt < 1 || throttleInt > 100) {
        console.log(`[PUT] Invalid throttle value: ${throttle}`)
        return { state: 'COMPLETED', statusCode: 400, message: `Invalid throttle '${throttle}'. Must be an integer from 1 to 100.` }
      }

      try {
        setManualMode(true)
        const throttleDecimal = throttleInt / 100
        setMotorThrottle(throttleDecimal)
        console.log(`[PUT] Motor throttle set to ${throttleInt}% (${throttleDecimal}, manual mode enabled)`)

        publishMotorState()
        return { state: 'COMPLETED', statusCode: 200 }
      } catch (error) {
        console.error(`[PUT] Motor throttle error:`, error)
        return { state: 'COMPLETED', statusCode: 500, message: error.message }
      }
    }
  )

  console.log('Motor PUT handlers registered:')
  console.log('  - PUT navigation.anchor.motor.state (forward/backward/stop)')
  console.log('  - PUT navigation.anchor.motor.throttle (1-100)')
}

module.exports = {
  // Main API (compatible with V1)
  runTestSequence,
  stopTestSimulation,
  setBoatPosition,
  moveToZone,
  startMotoring,
  startMotoringBackwards,
  stopMotoring,
  setMotorPower,
  moveSouth,

  // Data access
  getTestData,
  clearTestData,

  // V2-specific API
  getSimulationState,
  updateSimulationConfig,
  resetSimulation,

  // Test endpoint registration
  registerTestRouterEndpoints,
  registerMotorPutHandlers,

  // Direct access for testing
  _internal: {
    boat: () => boat,
    environment: () => environment,
    integrator: () => integrator,
  }
}

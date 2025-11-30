// Test simulation for anchor behavior with wind-based physics
// This file should NOT be included in production builds

// testing variables
let windSpeed = 10 // knots
let windDirection = 0 // degrees true (0 = North)
let boatVelocityX = 0 // m/s east-west
let boatVelocityY = 0 // m/s north-south
let testInterval = null
let windInterval = null

// Position state - needs to be module-level so setBoatPosition can access it
let currentLat = null
let currentLon = null
let sendChangeCallback = null
let manualMoveGracePeriod = 0 // Iterations remaining in grace period after manual move
let virtualAnchorLat = null // Virtual anchor position for physics (not in SignalK)
let virtualAnchorLon = null // Virtual anchor position for physics (not in SignalK)
let previousRodeDeployed = 0 // Track previous rode for chain-raising detection
let gradualMoveDistance = 0 // Remaining distance (m) to move toward anchor gradually
let gradualMoveIterations = 10 // Spread movement over this many iterations for smooth motion
let motoringActive = false // Track if motor is running forward
let motoringBackwardsActive = false // Track if motor is running backwards
let motoringApp = null // Store app reference for motoring

// Data logging for testing framework
let testDataLog = []
let loggingEnabled = false
let testStartTime = null

/**
 * Runs a realistic wind-based anchor test simulation
 * @param {object} app - SignalK app object
 * @param {function} sendChange - Function to send SignalK updates
 * @param {object} options - Optional configuration {enableLogging: boolean}
 */
function runTestSequence(app, sendChange, options = {}) {
    console.log('Starting wind-based anchor test simulation...')

    // Initialize logging
    loggingEnabled = options.enableLogging || false
    if (loggingEnabled) {
        testDataLog = []
        testStartTime = Date.now()
        console.log('Data logging enabled')
    }

    // Reset global velocity variables to ensure clean start
    boatVelocityX = 0
    boatVelocityY = 0
    windSpeed = 10
    windDirection = 180

    // Reset virtual anchor (will be set to real anchor position when anchor is dropped)
    virtualAnchorLat = null
    virtualAnchorLon = null

    console.log(`========== INITIALIZATION COMPLETE ==========`)
    console.log(`Velocities: boatVelocityX=${boatVelocityX}, boatVelocityY=${boatVelocityY}`)
    console.log(`Wind: speed=${windSpeed}, direction=${windDirection}`)
    console.log(`============================================`)

    // Initial test conditions
    const testDepth = 3 // meters - reduced from 5m to allow proper catenary physics with initial chain deployment
    const initialLat = 43.59738
    const initialLon = -79.5073

    // Maintain position state at module level (so setBoatPosition can access it)
    currentLat = initialLat
    currentLon = initialLon
    sendChangeCallback = sendChange

    console.log(`Position initialized: currentLat=${currentLat}, currentLon=${currentLon}`)

    sendChange('environment.depth.belowSurface', testDepth)
    sendChange('navigation.position', {
        longitude: currentLon,
        latitude: currentLat,
    })
    console.log(`Initial position set: ${currentLat}, ${currentLon}`)

    // Clear any old anchor position by setting to null first
    sendChange('navigation.anchor.position', null)
    console.log('Cleared old anchor position')

    // Initialize wind with moderate conditions
    windSpeed = 10 // knots
    windDirection = 180 // degrees (blowing from south, pushing boat north)

    // Set initial heading to point into the wind (toward wind source)
    const initialHeading = (windDirection * Math.PI) / 180
    sendChange('navigation.headingTrue', initialHeading)

    console.log(
        `Test sequence initialized. Wind: ${windSpeed} knots from ${windDirection}°, Boat heading: ${Math.round(windDirection)}°`
    )

    // Note: No initial drift velocity - wind force will naturally move the boat
    // This prevents corruption from external data sources setting rode deployment

    // Conversion constants (approximate for latitude ~43°)
    const METERS_TO_LAT = 0.000009 // 1 meter ≈ 0.000009° latitude
    const METERS_TO_LON = 0.0000125 // 1 meter ≈ 0.0000125° longitude at 43°N

    // Physics constants
    const BOAT_MASS = 15875 // kg (35,000 lbs)
    const WATER_DRAG = 20.0 // drag coefficient (balanced for wind-driven movement during deployment)
    const RODE_SPRING_CONSTANT = 0.8 // how much rode acts like a spring
    const DT = 0.5 // time step in seconds
    const bowHeight = 2 // meters

    // Wind variation - simulates gusts and shifts
    windInterval = setInterval(() => {
        // Add random gusts (±3 knots)
        const gust = (Math.random() - 0.5) * 6
        windSpeed = Math.max(5, Math.min(20, windSpeed + gust))

        // Gradual wind shift (±2° every 10 seconds)
        windDirection += (Math.random() - 0.5) * 4
        if (windDirection < 0) windDirection += 360
        if (windDirection >= 360) windDirection -= 360

        // Update wind data in SignalK
        sendChange('environment.wind.speedTrue', windSpeed * 0.514444) // knots to m/s
        sendChange('environment.wind.directionTrue', (windDirection * Math.PI) / 180) // degrees to radians

        if (Math.random() < 0.1) {
            // 10% chance to log wind changes
            console.log(
                `Wind update: ${windSpeed.toFixed(1)} knots from ${Math.round(windDirection)}°`
            )
        }
    }, 10000) // Update wind every 10 seconds

    // Data logging function - called each iteration if logging enabled
    function logTestData(state) {
        if (!loggingEnabled) return

        const elapsed = Date.now() - testStartTime
        testDataLog.push({
            timestamp: elapsed,
            lat: state.lat,
            lon: state.lon,
            heading: state.heading,
            velocityX: state.velocityX,
            velocityY: state.velocityY,
            distance: state.distance,
            windSpeed: state.windSpeed,
            windDirection: state.windDirection,
            chainSlack: state.chainSlack,
            rodeDeployed: state.rodeDeployed,
            chainDirection: state.chainDirection,
            motorActive: state.motorActive,
            motorBackwardsActive: state.motorBackwardsActive,
            windForce: state.windForce,
            rodeTension: state.rodeTension
        })
    }

    // Export function to retrieve logged data
    if (typeof module !== 'undefined' && module.exports) {
        module.exports.getTestData = () => testDataLog
        module.exports.clearTestData = () => { testDataLog = [] }
    }

    // Main physics simulation loop
    testInterval = setInterval(() => {
        // Debug: log values at start of iteration
        console.log(`>>> Physics loop iteration: currentLat=${currentLat}, currentLon=${currentLon}, boatVelX=${boatVelocityX}, boatVelY=${boatVelocityY}`)

        const currentDepth =
            app.getSelfPath('environment.depth.belowSurface')?.value ||
            testDepth
        const currentRodeDeployed =
            app.getSelfPath('navigation.anchor.rodeDeployed')?.value || 0

        // Monitor chain direction for auto-retrieve boat movement
        const chainDirection = app.getSelfPath('navigation.anchor.chainDirection')?.value

        // Detect chain being raised and set up gradual boat movement toward anchor
        if (chainDirection === 'up' && previousRodeDeployed > 0) {
            const chainRaised = previousRodeDeployed - currentRodeDeployed

            if (chainRaised > 0.1) { // Significant raise (>10cm)
                // Calculate horizontal distance freed using Pythagorean theorem
                let horizontalFreed = 0
                if (chainRaised > currentDepth) {
                    horizontalFreed = Math.sqrt(
                        Math.pow(chainRaised, 2) - Math.pow(currentDepth, 2)
                    )
                } else {
                    // If chain raised is less than depth, most of it is vertical
                    horizontalFreed = chainRaised * 0.2 // Estimate 20% horizontal component
                }

                // Add slack creation distance for next retrieval cycle
                const slackCreationDistance = 2.5 // meters
                const totalMoveDistance = horizontalFreed + slackCreationDistance

                // Set up gradual movement (will be applied over multiple iterations)
                gradualMoveDistance = totalMoveDistance

                console.log(`Chain raised ${chainRaised.toFixed(2)}m, ` +
                           `freed ${horizontalFreed.toFixed(2)}m horizontal, ` +
                           `will move ${totalMoveDistance.toFixed(2)}m toward anchor gradually over ${gradualMoveIterations} iterations`)
            }
        } else if (chainDirection === 'down' && previousRodeDeployed > 0) {
            // Detect chain being lowered and set up gradual boat movement away from anchor
            const chainLowered = currentRodeDeployed - previousRodeDeployed

            // CRITICAL: During initial deployment (rode < 7m), DO NOT use gradualMove mechanism
            // This would artificially limit boat movement over 10 iterations, causing slack violations
            // Let natural wind drift handle the movement instead - it's much faster and more physical
            const INITIAL_DEPLOYMENT_LIMIT_LOCAL = currentDepth + 2 + 2  // Same as slack constraint limit
            const isInitialDeployment = currentRodeDeployed < INITIAL_DEPLOYMENT_LIMIT_LOCAL

            if (chainLowered > 0.1 && !isInitialDeployment) { // Significant lowering, but NOT during initial phase
                // Calculate horizontal distance needed using Pythagorean theorem
                // As chain deploys, boat drifts outward to accommodate the new length
                let horizontalDrift = 0
                if (chainLowered > currentDepth) {
                    horizontalDrift = Math.sqrt(
                        Math.pow(chainLowered, 2) - Math.pow(currentDepth, 2)
                    )
                } else {
                    // If chain lowered is less than depth, most is vertical
                    horizontalDrift = chainLowered * 0.2 // Estimate 20% horizontal component
                }

                // Set up gradual movement away from anchor (opposite of retrieval)
                // Negative value indicates movement away from anchor
                gradualMoveDistance = -horizontalDrift

                console.log(`Chain lowered ${chainLowered.toFixed(2)}m, ` +
                           `will drift ${horizontalDrift.toFixed(2)}m away from anchor gradually over ${gradualMoveIterations} iterations`)
            } else if (isInitialDeployment && chainLowered > 0.1) {
                // During initial deployment, log but don't use gradual move
                console.log(`[INITIAL DEPLOYMENT] Chain lowered ${chainLowered.toFixed(2)}m - allowing natural wind drift (no gradual move constraint)`)
            }
        }

        // Update previous rode for next iteration
        previousRodeDeployed = currentRodeDeployed

        const anchorPos = app.getSelfPath('navigation.anchor.position')?.value
        const distance =
            app.getSelfPath('navigation.anchor.distanceFromBow')?.value || 0

        // Initialize virtual anchor when real anchor becomes available
        // Virtual anchor stays at the anchor position and only changes during moveToZone
        if (anchorPos &&
            typeof anchorPos.latitude === 'number' &&
            typeof anchorPos.longitude === 'number' &&
            (virtualAnchorLat === null || virtualAnchorLon === null)) {
            virtualAnchorLat = anchorPos.latitude
            virtualAnchorLon = anchorPos.longitude
            console.log(`Virtual anchor initialized to real anchor position: ${virtualAnchorLat}, ${virtualAnchorLon}`)
        }

        // During deployment (chainDirection === 'down'), auto-set anchor position if not already set
        // This allows physics to run even if the real chain controller hasn't set anchor position yet
        if (chainDirection === 'down' && (!anchorPos ||
            typeof anchorPos.latitude !== 'number' ||
            typeof anchorPos.longitude !== 'number')) {
            // Auto-set anchor position at boat's current location
            anchorPos = {
                latitude: currentLat,
                longitude: currentLon
            }
            // Also update virtual anchor to match
            if (virtualAnchorLat === null || virtualAnchorLon === null) {
                virtualAnchorLat = currentLat
                virtualAnchorLon = currentLon
                console.log(`Virtual anchor initialized to boat position for initial deployment drift: ${virtualAnchorLat}, ${virtualAnchorLon}`)
            }
            // Auto-publish the anchor position so it's available in SignalK
            sendChange('navigation.anchor.position', {
                latitude: currentLat,
                longitude: currentLon,
                altitude: 0
            })
            console.log(`Anchor position auto-set to boat position: ${currentLat}, ${currentLon}`)
        } else if (!anchorPos ||
            typeof anchorPos.latitude !== 'number' ||
            typeof anchorPos.longitude !== 'number') {
            // Not deploying and no real anchor - wait
            console.log('WARNING: anchor position not set yet, waiting...')
            return
        }

        console.log(`>>> After anchor check: anchor is valid, continuing with physics...`)

        // Calculate maximum swing radius based on catenary (simplified)
        // Max horizontal distance = sqrt(rode² - (depth + bowHeight)²)
        const verticalRode = currentDepth + bowHeight
        const maxSwingRadius = Math.sqrt(
            Math.max(
                0,
                Math.pow(currentRodeDeployed, 2) - Math.pow(verticalRode, 2)
            )
        )

        // Wind force calculation
        // Convert wind direction to radians (direction wind is blowing TO)
        const windAngleRad = (((windDirection + 180) % 360) * Math.PI) / 180
        const windSpeedMs = windSpeed * 0.514444 // knots to m/s

        // Wind force proportional to speed squared
        // F = 0.5 * ρ * A * Cd * v²
        // Using effective windage area of ~30m² for a sailboat
        const AIR_DENSITY = 1.2 // kg/m³
        const WINDAGE_AREA = 30 // m² (frontal area exposed to wind)
        const DRAG_COEFFICIENT = 1.0 // typical for boats
        const windForce = 0.5 * AIR_DENSITY * WINDAGE_AREA * DRAG_COEFFICIENT * windSpeedMs * windSpeedMs
        const windForceX = windForce * Math.sin(windAngleRad) // East component
        const windForceY = windForce * Math.cos(windAngleRad) // North component

        // CRITICAL: Ensure virtual anchor is initialized before physics calculations
        // This is a safety fallback in case both initialization conditions above weren't met
        if (virtualAnchorLat === null || virtualAnchorLon === null) {
            virtualAnchorLat = currentLat
            virtualAnchorLon = currentLon
            console.log(`Virtual anchor initialized (safety fallback) to boat position: ${virtualAnchorLat}, ${virtualAnchorLon}`)
        }

        // Calculate direction AND distance from boat to virtual anchor for physics
        // Virtual anchor is used for force calculations to prevent explosions after manual moves
        // Real anchor (anchorPos) is still used by alarm system for distance triggers
        const physicsAnchorLat = virtualAnchorLat
        const physicsAnchorLon = virtualAnchorLon
        const deltaLat = physicsAnchorLat - currentLat
        const deltaLon = physicsAnchorLon - currentLon
        const angleToAnchor = Math.atan2(deltaLon, deltaLat)

        // Calculate distance to virtual anchor for physics (not real anchor distance)
        // Convert lat/lon delta to meters (approximate)
        const METERS_TO_LAT = 0.000009
        const METERS_TO_LON = 0.0000125
        const deltaLatMeters = deltaLat / METERS_TO_LAT
        const deltaLonMeters = deltaLon / METERS_TO_LON
        const distanceToVirtualAnchor = Math.sqrt(deltaLatMeters * deltaLatMeters + deltaLonMeters * deltaLonMeters)

        // Rode tension force (acts as restoring force toward anchor)
        let rodeTensionX = 0
        let rodeTensionY = 0

        // CRITICAL FIX: During anchor deployment (chainDirection === 'down'), the rope is SLACK
        // and cannot support the boat. Do NOT apply any rode tension during deployment - only wind
        // Once anchor is dropped and settled (rode > 7.5m), rope becomes taut and can support the boat
        if (distanceToVirtualAnchor > 0 && chainDirection !== 'down') {

            // Rode tension: spring force + velocity damping to prevent bounce
            // Based on real-world anchoring: rode acts as spring-damper system

            // Calculate tension adjustment based on chain retrieval
            let tensionMultiplier = 1.0  // Default multiplier

            if (chainDirection === 'up') {
                // During retrieval: increase tension based on suspended chain weight
                // Suspended chain weight = chain in water (rode - vertical component)
                const verticalRode = currentDepth + bowHeight
                const suspendedChainLength = Math.max(0, currentRodeDeployed - verticalRode)
                // Apply about 50% of suspended chain weight as proportional force
                // Normalize by relating to typical wind force
                const chainWeightForce = suspendedChainLength * 50  // ~50 N per meter of suspended chain
                tensionMultiplier = 1.0 + (chainWeightForce / windForce) * 0.5  // 50% of normalized weight
                tensionMultiplier = Math.min(tensionMultiplier, 2.0)  // Cap at 2x for stability
            }

            let springForce = 0

            if (maxSwingRadius < 1.0) {
                // Special case: rode barely deployed, use simple spring model
                // Acts like a very stiff spring pulling boat back to anchor
                springForce = windForce * 2.0 * (distanceToVirtualAnchor / 1.0) * tensionMultiplier
            } else if (distanceToVirtualAnchor < maxSwingRadius * 0.7) {
                // Free drift zone: no spring force (even during retrieval)
                springForce = 0
            } else if (distanceToVirtualAnchor < maxSwingRadius * 0.95) {
                // Deceleration zone: rode tension < wind force for gradual slowdown
                const excessRatio = (distanceToVirtualAnchor - maxSwingRadius * 0.7) / (maxSwingRadius * 0.25)
                springForce = windForce * Math.pow(excessRatio, 2) * 0.8 * tensionMultiplier
            } else {
                // Hard stop zone: prevent exceeding catenary limit
                const excessRatio = (distanceToVirtualAnchor - maxSwingRadius * 0.95) / (maxSwingRadius * 0.05)
                // Cap excessRatio to prevent exponential explosion
                const cappedRatio = Math.min(excessRatio, 5.0)
                springForce = windForce * 0.8 + windForce * Math.pow(cappedRatio, 6) * 10 * tensionMultiplier
            }

            // Add velocity damping: opposes motion along rode direction
            // This dissipates energy and prevents elastic bounce
            const velocityAlongRode =
                (boatVelocityX * Math.sin(angleToAnchor) +
                 boatVelocityY * Math.cos(angleToAnchor))
            // Damping opposes velocity (negative sign), coefficient tuned for critical damping
            const dampingForce = -velocityAlongRode * BOAT_MASS * 0.5

            let rodeTension = springForce + dampingForce

            // CRITICAL: Cap rode tension to prevent explosions when boat is far from anchor
            // Maximum reasonable rode tension is ~100x wind force (way beyond realistic)
            const maxRodeTension = windForce * 100
            if (Math.abs(rodeTension) > maxRodeTension) {
                rodeTension = Math.sign(rodeTension) * maxRodeTension
            }

            // Gradually ramp up rode tension after manual position changes
            // This prevents sudden shock when boat is moved to new position
            if (manualMoveGracePeriod > 0) {
                // Scale from 0% to 100% as grace period counts down from 10 to 0
                const rampUpFactor = (10 - manualMoveGracePeriod) / 10
                rodeTension *= rampUpFactor
            }

            rodeTensionX = rodeTension * Math.sin(angleToAnchor)
            rodeTensionY = rodeTension * Math.cos(angleToAnchor)
        }

        // Water drag force (opposes velocity)
        const dragForceX =
            -boatVelocityX * Math.abs(boatVelocityX) * WATER_DRAG
        const dragForceY =
            -boatVelocityY * Math.abs(boatVelocityY) * WATER_DRAG

        // AUTO-ENGAGEMENT: Motor backward as backup when wind is insufficient
        // Strategy: Let wind move the boat naturally, only engage motor if boat isn't moving enough
        const isDeploying = chainDirection === 'down'
        const isRodeIncreasing = currentRodeDeployed > previousRodeDeployed && currentRodeDeployed > 0.5

        // Check if boat is actually moving due to wind
        const boatMoving = Math.sqrt(boatVelocityX * boatVelocityX + boatVelocityY * boatVelocityY) > 0.2  // m/s threshold

        // During deployment, engage motor backward ONLY if wind is not moving the boat sufficiently
        const MOTOR_BACKWARD_ENGAGE_THRESHOLD = 7.5  // Engage after anchor hits bottom

        if (isDeploying && currentRodeDeployed >= MOTOR_BACKWARD_ENGAGE_THRESHOLD && !boatMoving && !motoringBackwardsActive) {
            // Anchor is settled, but wind alone isn't moving boat - engage motor as backup
            motoringBackwardsActive = true
            motoringActive = false  // Disable forward motor - mutual exclusion
            if (Math.random() < 0.05) {
                console.log(`[AUTO-ENGAGE] Motor BACKWARD engaged as backup (wind insufficient, rode=${currentRodeDeployed.toFixed(1)}m)`)
            }
        } else if (motoringBackwardsActive && boatMoving) {
            // Wind is now moving the boat, disable motor
            motoringBackwardsActive = false
            if (Math.random() < 0.05) {
                console.log(`[AUTO-DISENGAGE] Motor disabled (wind moving boat sufficiently)`)
            }
        } else if (motoringBackwardsActive && !isDeploying && currentRodeDeployed > INITIAL_DEPLOYMENT_LIMIT) {
            // Deployment ended, disengage motor
            motoringBackwardsActive = false
            if (Math.random() < 0.05) {
                console.log(`[AUTO-DISENGAGE] Motor stopped - deployment ended`)
            }
        }

        // Motor thrust force (heading-based, not anchor-based)
        let motorForceX = 0
        let motorForceY = 0
        if (motoringActive) {
            // Motor forward: thrust in direction of boat heading
            // Target speed: 1.0 m/s (1.94 knots) to overcome wind during retrieval
            const TARGET_MOTOR_SPEED = 1.0 // m/s

            // Calculate current velocity component in direction of heading
            const velocityAlongHeading =
                boatVelocityX * Math.sin(boatHeading) +
                boatVelocityY * Math.cos(boatHeading)

            // Speed error (how much slower we are than target)
            const speedError = TARGET_MOTOR_SPEED - velocityAlongHeading

            // Proportional thrust - increased gain to overcome wind
            const MOTOR_GAIN = BOAT_MASS * 0.5
            const motorThrust = speedError * MOTOR_GAIN

            // Apply thrust in direction of heading (forward)
            motorForceX = motorThrust * Math.sin(boatHeading)
            motorForceY = motorThrust * Math.cos(boatHeading)

            // Debug logging every ~2 seconds
            if (Math.random() < 0.02) {
                console.log(`Motor forward: thrust=${motorThrust.toFixed(1)}N, velAlong=${velocityAlongHeading.toFixed(2)}m/s, heading=${(boatHeading * 180 / Math.PI).toFixed(1)}°`)
            }
        } else if (motoringBackwardsActive && distanceToVirtualAnchor > 0) {
            // Motor backwards - apply thrust in OPPOSITE direction of boat heading (reverse thrust)
            // Stop if we reach the maximum swing radius
            if (distanceToVirtualAnchor >= maxSwingRadius * 0.90) {
                console.log(`Reached maximum swing radius (${distanceToVirtualAnchor.toFixed(1)}m / ${maxSwingRadius.toFixed(1)}m) - stopping backwards motor`)
                motoringBackwardsActive = false
            } else {
                // Apply reverse thrust: opposite to the boat's current heading
                // This makes the boat move backward away from the anchor
                const TARGET_MOTOR_SPEED = 1.5 // m/s (increased from 1.0 to overcome residual wind)

                // Calculate current velocity component in direction of heading
                const velocityAlongHeading =
                    boatVelocityX * Math.sin(boatHeading) +
                    boatVelocityY * Math.cos(boatHeading)

                // For reverse: we want negative velocity (opposite to heading)
                // So if boat is moving forward (positive velocity), we need strong negative thrust
                const speedError = -TARGET_MOTOR_SPEED - velocityAlongHeading

                // Proportional thrust - increased gain to overcome residual wind (15kn)
                const MOTOR_GAIN = BOAT_MASS * 0.75  // Increased from 0.5
                const motorThrust = speedError * MOTOR_GAIN

                // Apply thrust in OPPOSITE direction of heading (reverse)
                // Opposite heading = heading + 180° = heading + π
                const reverseHeading = boatHeading + Math.PI
                motorForceX = motorThrust * Math.sin(reverseHeading)
                motorForceY = motorThrust * Math.cos(reverseHeading)

                // Debug logging every ~2 seconds
                if (Math.random() < 0.02) {
                    console.log(`Motor BACKWARD: thrust=${motorThrust.toFixed(1)}N, velAlong=${velocityAlongHeading.toFixed(2)}m/s, heading=${(boatHeading * 180 / Math.PI).toFixed(1)}°, rode=${currentRodeDeployed.toFixed(1)}m`)
                }
            }
        }

        // Net force and acceleration
        const netForceX = windForceX + rodeTensionX + dragForceX + motorForceX
        const netForceY = windForceY + rodeTensionY + dragForceY + motorForceY

        const accelX = netForceX / BOAT_MASS
        const accelY = netForceY / BOAT_MASS

        // Debug: check for NaN or Infinity in forces/acceleration
        if (isNaN(accelX) || isNaN(accelY) || isNaN(boatVelocityX) || isNaN(boatVelocityY) ||
            !isFinite(accelX) || !isFinite(accelY) || !isFinite(boatVelocityX) || !isFinite(boatVelocityY)) {
            console.log(`NaN/Infinity detected! accelX=${accelX}, accelY=${accelY}, boatVelX=${boatVelocityX}, boatVelY=${boatVelocityY}`)
            console.log(`Forces: windX=${windForceX}, windY=${windForceY}, rodeX=${rodeTensionX}, rodeY=${rodeTensionY}, dragX=${dragForceX}, dragY=${dragForceY}`)
            console.log(`angleToAnchor=${angleToAnchor}, distance=${distance}, maxSwingRadius=${maxSwingRadius.toFixed(2)}`)
            console.log(`springForce would be calculated from distance=${distance}`)
            console.log(`currentLat=${currentLat}, currentLon=${currentLon}`)
            console.log(`anchorPos:`, anchorPos)
            console.log(`STOPPING SIMULATION DUE TO NaN/Infinity ERROR`)
            stopTestSimulation()
            return
        }

        // Update velocity
        boatVelocityX += accelX * DT
        boatVelocityY += accelY * DT

        // Update position
        let deltaX = boatVelocityX * DT // meters
        let deltaY = boatVelocityY * DT // meters

        // Apply gradual movement (toward or away from anchor)
        if (Math.abs(gradualMoveDistance) > 0.01) {
            // Move a fraction of the remaining distance each iteration
            const moveThisIteration = gradualMoveDistance / gradualMoveIterations

            // Calculate direction to/from anchor (for gradual movement, use real anchor not virtual)
            const deltaLatToAnchor = anchorPos.latitude - currentLat
            const deltaLonToAnchor = anchorPos.longitude - currentLon
            const angleToRealAnchor = Math.atan2(deltaLonToAnchor, deltaLatToAnchor)

            // If moveThisIteration is negative, movement is away from anchor (opposite direction)
            // Add gradual movement toward anchor (or away if negative)
            const gradualDeltaX = moveThisIteration * Math.sin(angleToRealAnchor)
            const gradualDeltaY = moveThisIteration * Math.cos(angleToRealAnchor)

            deltaX += gradualDeltaX
            deltaY += gradualDeltaY

            // Reduce remaining distance (handles both positive and negative)
            if (gradualMoveDistance > 0) {
                gradualMoveDistance -= moveThisIteration
            } else {
                gradualMoveDistance -= moveThisIteration  // Both are negative, so this increases toward zero
            }

            if (Math.random() < 0.2) { // Log occasionally
                const direction = moveThisIteration > 0 ? 'toward' : 'away from'
                console.log(`Gradual move: ${Math.abs(moveThisIteration).toFixed(2)}m ${direction} anchor, ${Math.abs(gradualMoveDistance).toFixed(2)}m remaining`)
            }
        }

        currentLon = currentLon + deltaX * METERS_TO_LON
        currentLat = currentLat + deltaY * METERS_TO_LAT

        // Debug: log if position becomes null
        if (currentLon === null || currentLat === null || isNaN(currentLon) || isNaN(currentLat)) {
            console.log(`ERROR: Position became invalid! currentLon=${currentLon}, currentLat=${currentLat}, deltaX=${deltaX}, deltaY=${deltaY}`)
        }

        // CRITICAL: Enforce slack constraint - boat cannot move beyond deployed chain length
        // HOWEVER: During initial deployment phase, allow natural drift without constraint
        // This lets the boat move away from the anchor as the chain is being deployed
        // to reach the seabed (depth + bowHeight + starting slack)
        // Initial deployment naturally reaches ~7m (depth 3m + bowHeight 2m + slack 2m)
        // Once rode exceeds this, re-enable slack constraint to prevent excessive drift
        const INITIAL_DEPLOYMENT_LIMIT = 7  // depth(3) + bowHeight(2) + slack(2) = natural stopping point
        const allowSlackConstraint = currentRodeDeployed > INITIAL_DEPLOYMENT_LIMIT || chainDirection === 'up'

        // Calculate current distance from virtual anchor with new position
        const newDeltaLat = virtualAnchorLat - currentLat
        const newDeltaLon = virtualAnchorLon - currentLon
        const newDeltaLatMeters = newDeltaLat / METERS_TO_LAT
        const newDeltaLonMeters = newDeltaLon / METERS_TO_LON
        const newDistanceToAnchor = Math.sqrt(newDeltaLatMeters * newDeltaLatMeters + newDeltaLonMeters * newDeltaLonMeters)

        // Calculate slack with new distance
        const newSlack = currentRodeDeployed - newDistanceToAnchor

        // Slack constraint: boat cannot exceed deployed rope length
        // When slack < 0, clamp boat position back to the slack=0 boundary
        if (allowSlackConstraint && chainDirection !== 'up') {
            if (newSlack < 0) {
                // Progressive constraint: gently slow boat as it approaches limit
                // This prevents jerky bouncing from hard velocity clamps
                // BUT: motor backward may push boat backward, so allow more motion

                // Calculate how much slack we've exceeded (negative slack is excess)
                const slackViolation = Math.abs(newSlack)  // Positive excess distance
                const violationFraction = Math.min(1.0, slackViolation / (currentRodeDeployed * 0.1))  // Fraction of rode length

                // Progressive damping: as violation increases, damping increases
                // At 0m violation: 0.98x (2% reduction)
                // At 10% of rode: 0.85x (15% reduction)
                // At 20%+ of rode: 0.70x (30% reduction)
                // WEAKENED from 0.95-0.50 to 0.98-0.70 to allow backward motion
                const dampingFactor = Math.max(0.70, 0.98 - violationFraction * 0.28)
                boatVelocityX *= dampingFactor
                boatVelocityY *= dampingFactor

                // Clamp position back, but only if significantly overshooting
                if (newDistanceToAnchor > 0.1 && slackViolation > 0.5) {
                    const scaleFactor = currentRodeDeployed / newDistanceToAnchor
                    // Scale deltas to position the boat exactly at rode distance from anchor
                    currentLat = virtualAnchorLat - (newDeltaLat * scaleFactor)
                    currentLon = virtualAnchorLon - (newDeltaLon * scaleFactor)
                }

                if (Math.random() < 0.05) {
                    console.log(`Slack constraint: progressive damping=${dampingFactor.toFixed(2)}, slack=${newSlack.toFixed(2)}m, violation=${slackViolation.toFixed(2)}m`)
                }
            }
        } else if (newSlack < 0 && !allowSlackConstraint && Math.random() < 0.02) {
            // Debug logging during initial deployment phase
            console.log(`[INITIAL DEPLOYMENT] Allowing natural drift: rode=${currentRodeDeployed.toFixed(1)}m, distance=${newDistanceToAnchor.toFixed(1)}m, slack=${newSlack.toFixed(2)}m`)
        }

        sendChange('navigation.position', {
            longitude: currentLon,
            latitude: currentLat,
        })

        // Update heading - implements two-phase heading behavior
        // Phase 1: Head-to-wind until rode > threshold
        // Phase 2: Anchor-constrained heading with transition
        const chainSlack = app.getSelfPath('navigation.anchor.chainSlack')?.value || 0
        let boatHeading

        // Phase thresholds (in meters of rode deployed)
        const EARLY_DEPLOYMENT_THRESHOLD = currentDepth + 10 + bowHeight  // ~13m at 3m depth
        const FULL_ANCHOR_CONSTRAINT_THRESHOLD = currentDepth + 40 + bowHeight  // ~45m at 3m depth

        if (currentRodeDeployed <= EARLY_DEPLOYMENT_THRESHOLD) {
            // Phase 1: Early deployment - boat heads into wind
            // This allows natural drift perpendicular to wind
            const windHeading = (windDirection * Math.PI) / 180
            // Add small random yaw variation (±10 degrees) for natural motion
            const yawVariation = (Math.random() - 0.5) * 2 * (10 * Math.PI / 180)
            boatHeading = windHeading + yawVariation
        } else if (currentRodeDeployed >= FULL_ANCHOR_CONSTRAINT_THRESHOLD) {
            // Phase 2b: Full anchor constraint - boat points toward anchor
            // This is full rode tension control
            const anchorHeading = angleToAnchor
            // Add small random yaw (±3 degrees) for natural swinging
            const yawVariation = (Math.random() - 0.5) * 2 * (3 * Math.PI / 180)
            boatHeading = anchorHeading + yawVariation
        } else {
            // Phase 2a: Transition zone - blend from wind to anchor heading
            // Linear interpolation between early deployment and full constraint thresholds
            const transitionFraction = (currentRodeDeployed - EARLY_DEPLOYMENT_THRESHOLD) /
                                       (FULL_ANCHOR_CONSTRAINT_THRESHOLD - EARLY_DEPLOYMENT_THRESHOLD)

            const windHeading = (windDirection * Math.PI) / 180
            const anchorHeading = angleToAnchor

            // Blend the headings: start with wind, transition to anchor
            boatHeading = windHeading * (1 - transitionFraction) + anchorHeading * transitionFraction

            // Add yaw that decreases as we transition (from ±10° to ±3°)
            const yawAmount = 10 - (transitionFraction * 7)  // 10° → 3°
            const yawVariation = (Math.random() - 0.5) * 2 * (yawAmount * Math.PI / 180)
            boatHeading = boatHeading + yawVariation
        }
        sendChange('navigation.headingTrue', boatHeading)

        // Publish calculated boat speed based on velocity
        const boatSpeed = Math.sqrt(boatVelocityX * boatVelocityX + boatVelocityY * boatVelocityY)
        sendChange('navigation.speedOverGround', boatSpeed)

        if (Math.random() < 0.02) {
            const headingDegrees = Math.round((boatHeading * 180 / Math.PI + 360) % 360)
            const anchorBearing = Math.round((angleToAnchor * 180 / Math.PI + 360) % 360)
            console.log(`Heading: ${headingDegrees}°, Anchor bearing: ${anchorBearing}°, Wind: ${Math.round(windDirection)}° @ ${windSpeed.toFixed(1)}kn, Speed: ${boatSpeed.toFixed(2)}m/s`)
        }

        // Occasional logging
        if (Math.random() < 0.02) {
            // 2% chance per iteration
            const velX = isNaN(boatVelocityX) ? 0 : boatVelocityX
            const velY = isNaN(boatVelocityY) ? 0 : boatVelocityY
            console.log(
                `Boat physics: dist=${distanceToVirtualAnchor.toFixed(1)}m, maxSwing=${maxSwingRadius.toFixed(1)}m, vel=(${velX.toFixed(2)},${velY.toFixed(2)})m/s, wind=${windSpeed.toFixed(1)}kt@${Math.round(windDirection)}°`
            )
        }

        // Decrement grace period counter
        if (manualMoveGracePeriod > 0) {
            manualMoveGracePeriod--
            if (manualMoveGracePeriod === 0) {
                console.log('Grace period ended - rode tension forces re-enabled')
            }
        }

        // Log test data if logging is enabled
        if (loggingEnabled) {
            const rodeTensionMagnitude = Math.sqrt(rodeTensionX * rodeTensionX + rodeTensionY * rodeTensionY)
            logTestData({
                lat: currentLat,
                lon: currentLon,
                heading: boatHeading,
                velocityX: boatVelocityX,
                velocityY: boatVelocityY,
                distance: distanceToVirtualAnchor,
                windSpeed: windSpeed,
                windDirection: windDirection,
                chainSlack: chainSlack,
                rodeDeployed: currentRodeDeployed,
                chainDirection: chainDirection,
                motorActive: motoringActive,
                motorBackwardsActive: motoringBackwardsActive,
                windForce: windForce,
                rodeTension: rodeTensionMagnitude
            })
        }

        // Keep depth constant for testing
        sendChange('environment.depth.belowSurface', testDepth)
    }, DT * 1000) // Run simulation at DT interval

    console.log(`Physics simulation running at ${DT} second intervals`)
}

/**
 * Stops the test simulation and clears intervals
 */
function stopTestSimulation() {
    if (testInterval) {
        clearInterval(testInterval)
        testInterval = null
    }
    if (windInterval) {
        clearInterval(windInterval)
        windInterval = null
    }

    // Reset velocity and grace period
    boatVelocityX = 0
    boatVelocityY = 0
    manualMoveGracePeriod = 0

    console.log('Test simulation stopped')
}

/**
 * Set boat position manually (for testing alarm triggers)
 * @param {number} lat - New latitude
 * @param {number} lon - New longitude
 */
function setBoatPosition(lat, lon, app) {
    if (currentLat === null || currentLon === null) {
        console.log('Warning: Cannot set boat position - simulation not initialized')
        return false
    }

    // Calculate how much we're moving the boat
    const deltaLat = lat - currentLat
    const deltaLon = lon - currentLon

    // Move the virtual anchor by the same amount to preserve relative geometry
    // This maintains the physics balance - boat continues normal drift at new location
    if (virtualAnchorLat !== null && virtualAnchorLon !== null) {
        virtualAnchorLat += deltaLat
        virtualAnchorLon += deltaLon
        console.log(`Virtual anchor moved by same delta to: ${virtualAnchorLat}, ${virtualAnchorLon}`)
    }

    currentLat = lat
    currentLon = lon

    // CRITICAL: Reset velocity when manually moving boat
    // Otherwise physics will calculate incorrect forces based on old velocity
    boatVelocityX = 0
    boatVelocityY = 0

    // Set grace period to prevent rode tension from creating huge forces
    // 10 iterations = 5 seconds at 0.5s per iteration
    manualMoveGracePeriod = 10

    if (sendChangeCallback) {
        sendChangeCallback('navigation.position', {
            latitude: lat,
            longitude: lon
        })
    }

    console.log(`Boat position manually set to: ${lat}, ${lon} (velocity reset, grace period active)`)
    return true
}

/**
 * Move boat to warning or alarm zone for testing
 * @param {object} app - SignalK app object
 * @param {string} zoneType - 'warn' or 'alarm'
 */
function moveToZone(app, zoneType) {
    // Only allow manual moves when test simulation is active
    if (testInterval === null) {
        return 'Error: Test simulation is not running. Enable testMode in plugin settings.'
    }

    if (currentLat === null || currentLon === null) {
        return 'Error: Simulation not initialized'
    }

    // Get anchor position
    const anchorPos = app.getSelfPath('navigation.anchor.position')?.value
    if (!anchorPos) {
        return 'Error: Anchor not set'
    }

    // Get anchor alarm zones
    const anchorMeta = app.getSelfPath('navigation.anchor.meta')?.value
    if (!anchorMeta || !anchorMeta.zones) {
        return 'Error: Anchor alarm zones not available'
    }

    // Find the target distance based on zone type
    let targetDistance
    if (zoneType === 'warn') {
        // Move to far end of warning zone (near upper boundary)
        // This gives room for drift while staying in zone long enough for alarm to trigger
        const warnZone = anchorMeta.zones.find(z => z.state === 'warn')
        if (!warnZone) {
            return 'Error: Warning zone not found in anchor metadata'
        }
        targetDistance = warnZone.upper - 1 // 1m before upper boundary
    } else if (zoneType === 'alarm') {
        // Move to just past the alarm threshold (emergency zone)
        const emergencyZone = anchorMeta.zones.find(z => z.state === 'emergency')
        if (!emergencyZone) {
            return 'Error: Emergency zone not found in anchor metadata'
        }
        targetDistance = emergencyZone.lower + 1 // 1m into emergency zone
    } else {
        return 'Error: Invalid zone type. Use "warn" or "alarm"'
    }

    // Calculate current direction from anchor to boat
    const deltaLat = currentLat - anchorPos.latitude
    const deltaLon = currentLon - anchorPos.longitude
    const currentDistance = Math.sqrt(deltaLat * deltaLat + deltaLon * deltaLon)

    if (currentDistance === 0) {
        return 'Error: Boat is at anchor position'
    }

    // Normalize direction vector
    const dirLat = deltaLat / currentDistance
    const dirLon = deltaLon / currentDistance

    // Calculate new position at target distance in same direction
    const newLat = anchorPos.latitude + dirLat * targetDistance * 0.000009 // ~1m = 0.000009° lat
    const newLon = anchorPos.longitude + dirLon * targetDistance * 0.0000125 // ~1m = 0.0000125° lon at 43°N

    // Update position using setBoatPosition (pass app for virtual anchor calculation)
    setBoatPosition(newLat, newLon, app)

    console.log(`Moved boat to ${zoneType} zone at ${targetDistance.toFixed(1)}m from anchor`)
    return `Moved to ${zoneType} zone (${targetDistance.toFixed(1)}m from anchor)`
}

/**
 * Start motoring toward anchor at 1 knot
 * @param {object} app - SignalK app object
 */
function startMotoring(app) {
    // Only allow when test simulation is active
    if (testInterval === null) {
        return 'Error: Test simulation is not running. Enable testMode in plugin settings.'
    }

    if (currentLat === null || currentLon === null) {
        return 'Error: Simulation not initialized'
    }

    // Get anchor position
    const anchorPos = app.getSelfPath('navigation.anchor.position')?.value
    if (!anchorPos) {
        return 'Error: Anchor not set'
    }

    motoringActive = true
    motoringBackwardsActive = false  // Disable backward motor - mutual exclusion
    motoringApp = app
    console.log('Motor started - motoring toward anchor at 1 knot')
    return 'Motor started - motoring toward anchor at 1 knot'
}

/**
 * Start motoring backwards (away from anchor) at 0.5 knots
 * Automatically stops when reaching maximum swing radius
 * @param {object} app - SignalK app object
 */
function startMotoringBackwards(app) {
    // Only allow when test simulation is active
    if (testInterval === null) {
        return 'Error: Test simulation is not running. Enable testMode in plugin settings.'
    }

    if (currentLat === null || currentLon === null) {
        return 'Error: Simulation not initialized'
    }

    // Get anchor position
    const anchorPos = app.getSelfPath('navigation.anchor.position')?.value
    if (!anchorPos) {
        return 'Error: Anchor not set'
    }

    motoringBackwardsActive = true
    motoringActive = false  // Disable forward motor - mutual exclusion
    motoringApp = app
    console.log('Motor started - motoring backwards (away from anchor) at 0.5 knots')
    return 'Motor started - motoring backwards (away from anchor) at 0.5 knots'
}

/**
 * Stop motoring (both forward and backwards)
 */
function stopMotoring() {
    if (!motoringActive && !motoringBackwardsActive) {
        return 'Motor already stopped'
    }

    const wasForward = motoringActive
    const wasBackwards = motoringBackwardsActive

    motoringActive = false
    motoringBackwardsActive = false
    motoringApp = null

    const direction = wasForward ? 'forward' : (wasBackwards ? 'backwards' : '')
    console.log(`Motor stopped (was ${direction})`)
    return `Motor stopped (was ${direction})`
}

module.exports = {
    runTestSequence,
    stopTestSimulation,
    setBoatPosition,
    moveToZone,
    startMotoring,
    startMotoringBackwards,
    stopMotoring,
}

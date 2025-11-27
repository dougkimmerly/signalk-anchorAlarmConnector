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
let smoothedRode = 0 // Smoothed rode value to prevent explosions from sudden changes
let manualMoveGracePeriod = 0 // Iterations remaining in grace period after manual move
let virtualAnchorLat = null // Virtual anchor position for physics (not in SignalK)
let virtualAnchorLon = null // Virtual anchor position for physics (not in SignalK)
let previousRodeDeployed = 0 // Track previous rode for chain-raising detection
let gradualMoveDistance = 0 // Remaining distance (m) to move toward anchor gradually
let gradualMoveIterations = 10 // Spread movement over this many iterations for smooth motion

/**
 * Runs a realistic wind-based anchor test simulation
 * @param {object} app - SignalK app object
 * @param {function} sendChange - Function to send SignalK updates
 */
function runTestSequence(app, sendChange) {
    console.log('Starting wind-based anchor test simulation...')

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
    const testDepth = 5 // meters
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
    const WATER_DRAG = 150.0 // drag coefficient (very high damping to prevent bounce)
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

    // Main physics simulation loop
    testInterval = setInterval(() => {
        // Debug: log values at start of iteration
        console.log(`>>> Physics loop iteration: currentLat=${currentLat}, currentLon=${currentLon}, boatVelX=${boatVelocityX}, boatVelY=${boatVelocityY}`)

        const currentDepth =
            app.getSelfPath('environment.depth.belowSurface')?.value ||
            testDepth
        const rawRodeDeployed =
            app.getSelfPath('navigation.anchor.rodeDeployed')?.value || 0

        // Smooth rode changes to prevent explosions from fluctuating data sources
        // Limit rode change to 1m per iteration (0.5s), preventing sudden drops
        const maxRodeChange = 1.0 // meters per iteration
        if (smoothedRode === 0) {
            smoothedRode = rawRodeDeployed // Initialize on first iteration
            console.log(`Rode initialized: raw=${rawRodeDeployed}m, smoothed=${smoothedRode}m`)
        } else {
            const rodeChange = rawRodeDeployed - smoothedRode
            if (Math.abs(rodeChange) > maxRodeChange) {
                smoothedRode += Math.sign(rodeChange) * maxRodeChange
                console.log(`Rode smoothing: raw=${rawRodeDeployed}m, smoothed=${smoothedRode}m (limited change)`)
            } else {
                smoothedRode = rawRodeDeployed
            }
        }
        const currentRodeDeployed = smoothedRode

        if (Math.random() < 0.05) {
            console.log(`Rode values: raw=${rawRodeDeployed}m, smoothed=${currentRodeDeployed}m`)
        }

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
        }

        // Update previous rode for next iteration
        previousRodeDeployed = currentRodeDeployed

        const anchorPos = app.getSelfPath('navigation.anchor.position')?.value
        const distance =
            app.getSelfPath('navigation.anchor.distanceFromBow')?.value || 0

        if (!anchorPos ||
            typeof anchorPos.latitude !== 'number' ||
            typeof anchorPos.longitude !== 'number') {
            console.log('WARNING: anchor position not set yet, waiting...')
            return // Wait until anchor is set with valid coordinates
        }

        // Initialize virtual anchor to real anchor position on first valid anchor
        if (virtualAnchorLat === null || virtualAnchorLon === null) {
            virtualAnchorLat = anchorPos.latitude
            virtualAnchorLon = anchorPos.longitude
            console.log(`Virtual anchor initialized to real anchor position: ${virtualAnchorLat}, ${virtualAnchorLon}`)
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

        if (distanceToVirtualAnchor > 0) {

            // Rode tension: spring force + velocity damping to prevent bounce
            // Based on real-world anchoring: rode acts as spring-damper system
            let springForce = 0

            if (maxSwingRadius < 1.0) {
                // Special case: rode barely deployed, use simple spring model
                // Acts like a very stiff spring pulling boat back to anchor
                springForce = windForce * 2.0 * (distanceToVirtualAnchor / 1.0)
            } else if (distanceToVirtualAnchor < maxSwingRadius * 0.7) {
                // Free drift zone: no spring force
                springForce = 0
            } else if (distanceToVirtualAnchor < maxSwingRadius * 0.95) {
                // Deceleration zone: rode tension < wind force for gradual slowdown
                const excessRatio = (distanceToVirtualAnchor - maxSwingRadius * 0.7) / (maxSwingRadius * 0.25)
                springForce = windForce * Math.pow(excessRatio, 2) * 0.8
            } else {
                // Hard stop zone: prevent exceeding catenary limit
                const excessRatio = (distanceToVirtualAnchor - maxSwingRadius * 0.95) / (maxSwingRadius * 0.05)
                // Cap excessRatio to prevent exponential explosion
                const cappedRatio = Math.min(excessRatio, 5.0)
                springForce = windForce * 0.8 + windForce * Math.pow(cappedRatio, 6) * 10
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

        // Net force and acceleration
        const netForceX = windForceX + rodeTensionX + dragForceX
        const netForceY = windForceY + rodeTensionY + dragForceY

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

        // Apply gradual movement toward anchor if chain is being raised
        if (gradualMoveDistance > 0.01) {
            // Move a fraction of the remaining distance each iteration
            const moveThisIteration = gradualMoveDistance / gradualMoveIterations

            // Calculate direction to anchor (for gradual movement, use real anchor not virtual)
            const deltaLatToAnchor = anchorPos.latitude - currentLat
            const deltaLonToAnchor = anchorPos.longitude - currentLon
            const angleToRealAnchor = Math.atan2(deltaLonToAnchor, deltaLatToAnchor)

            // Add gradual movement toward anchor
            const gradualDeltaX = moveThisIteration * Math.sin(angleToRealAnchor)
            const gradualDeltaY = moveThisIteration * Math.cos(angleToRealAnchor)

            deltaX += gradualDeltaX
            deltaY += gradualDeltaY

            // Reduce remaining distance
            gradualMoveDistance -= moveThisIteration

            if (Math.random() < 0.2) { // Log occasionally
                console.log(`Gradual move: ${moveThisIteration.toFixed(2)}m toward anchor, ${gradualMoveDistance.toFixed(2)}m remaining`)
            }
        }

        currentLon = currentLon + deltaX * METERS_TO_LON
        currentLat = currentLat + deltaY * METERS_TO_LAT

        // Debug: log if position becomes null
        if (currentLon === null || currentLat === null || isNaN(currentLon) || isNaN(currentLat)) {
            console.log(`ERROR: Position became invalid! currentLon=${currentLon}, currentLat=${currentLat}, deltaX=${deltaX}, deltaY=${deltaY}`)
        }

        sendChange('navigation.position', {
            longitude: currentLon,
            latitude: currentLat,
        })

        // Update heading - with wind >5kn, rode tension keeps bow pointing toward anchor
        let boatHeading
        if (windSpeed > 5) {
            // Boat points toward anchor (rode tension dominates)
            // Add small random yaw variation (±5 degrees)
            const yawVariation = (Math.random() - 0.5) * 2 * (5 * Math.PI / 180) // ±5 degrees in radians
            boatHeading = angleToAnchor + yawVariation
        } else {
            // Light wind: boat can swing more freely, influenced by wind direction
            const windHeading = (windDirection * Math.PI) / 180
            // Blend between anchor direction and wind direction based on wind strength
            const windInfluence = windSpeed / 5 // 0 to 1
            boatHeading = angleToAnchor * (1 - windInfluence) + windHeading * windInfluence
        }
        sendChange('navigation.headingTrue', boatHeading)

        if (Math.random() < 0.02) {
            const headingDegrees = Math.round((boatHeading * 180 / Math.PI + 360) % 360)
            const anchorBearing = Math.round((angleToAnchor * 180 / Math.PI + 360) % 360)
            console.log(`Heading: ${headingDegrees}°, Anchor bearing: ${anchorBearing}°, Wind: ${Math.round(windDirection)}° @ ${windSpeed.toFixed(1)}kn`)
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

    // Reset velocity, smoothed rode, and grace period
    boatVelocityX = 0
    boatVelocityY = 0
    smoothedRode = 0
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

module.exports = {
    runTestSequence,
    stopTestSimulation,
    setBoatPosition,
    moveToZone,
}
